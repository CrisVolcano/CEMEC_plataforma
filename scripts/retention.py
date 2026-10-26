"""Inventario de retención. No elimina archivos; falla si no puede proteger referencias."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import yaml

def references(value):
    found=set()
    if isinstance(value,dict):
        for v in value.values(): found.update(references(v))
    elif isinstance(value,list):
        for v in value: found.update(references(v))
    elif isinstance(value,str):
        match=re.match(r'^/live-data/(v-[A-Za-z0-9_-]+)/',value)
        if match: found.add(match[1])
    return found

def read(path): return json.loads(path.read_text())

def plan(project,config,now=None):
    project=Path(project).resolve();now=time.time() if now is None else now
    policy=config['retention']
    for key in ('olci_unused_days','temporary_hours','snapshot_days','keep_previous_snapshots','job_log_days'):
        if type(policy[key]) is not int or policy[key]<1: raise ValueError('Plazo de retención inválido: '+key)
    if policy.get('preserve_history') is not True: raise ValueError('Debe preservarse el histórico')
    def safe(relative):
        path=(project/relative).resolve()
        if not path.is_relative_to(project/'runtime'): raise ValueError('La retención solo admite rutas dentro de runtime/')
        return path
    runtime=safe(config['firms']['storage']);snapshots=runtime/'snapshots'
    active=read(runtime/'active.json') if (runtime/'active.json').is_file() else None
    candidates=[];protected=[];notes=[]
    def newest(path):
        if path.is_symlink(): raise ValueError('Se detectó un enlace simbólico: '+str(path))
        files=[path]+list(path.rglob('*')) if path.is_dir() else [path]
        if any(f.is_symlink() for f in files): raise ValueError('Se detectó un enlace simbólico en '+str(path))
        return max(f.stat().st_mtime for f in files)
    def record(path,reason,collection):
        files=list(path.rglob('*')) if path.is_dir() else [path]
        collection.append({'path':str(path.relative_to(project)),
            'bytes':sum(f.stat().st_size for f in files if f.is_file()),'reason':reason})
    versions={p.name:p for p in snapshots.glob('v-*') if p.is_dir()}
    keep=set()
    if versions and active is None: raise ValueError('Hay snapshots pero falta active.json: se detiene el inventario')
    if active:
        keep=references(active);version=active['catalog']['version']
        if version in versions: keep.add(version)
        previous=sorted((p for k,p in versions.items() if k!=version),key=newest,reverse=True)
        keep.update(p.name for p in previous[:policy['keep_previous_snapshots']])
        keep.update(k for k,p in versions.items() if now-newest(p)<policy['snapshot_days']*86400)
        # Cierre de referencias: un snapshot conservado puede usar geometrías anteriores.
        pending=list(keep);seen=set()
        while pending:
            key=pending.pop()
            if key in seen: continue
            seen.add(key)
            if key not in versions: raise ValueError('Referencia activa sin snapshot: '+key)
            catalog=versions[key]/'catalog.json'
            if not catalog.is_file(): raise ValueError('Snapshot conservado sin catálogo: '+key)
            related=references(read(catalog));pending.extend(related-seen);keep.update(related)
    for key,path in versions.items():
        record(path,'Activo, reciente, última versión de respaldo o referenciado' if key in keep else 'Snapshot anterior al plazo, fuera de las versiones protegidas',protected if key in keep else candidates)
    caches=[('OLCI',safe(config.get('olci',{}).get('cache','runtime/olci')),policy['olci_unused_days']),
            ('Sentinel-2',safe(config.get('sentinel2',{}).get('cache','runtime/sentinel2')),policy.get('sentinel2_unused_days',policy['olci_unused_days']))]
    for label,cache,days in caches:
        if type(days) is not int or days<1: raise ValueError('Plazo de caché inválido: '+label)
        for path in cache.glob('*'):
            if path.is_dir() and re.fullmatch(r'[0-9a-f]{64}',path.name):
                if not (path/'metadata.json').is_file() or not (path/'image.png').is_file():
                    record(path,'Caché incompleta; requiere revisar tareas antes de eliminar',protected);continue
                age=now-newest(path)
                record(path,label+' sin uso durante el plazo' if age>=days*86400 else label+' reciente o utilizado',candidates if age>=days*86400 else protected)
    for path in (runtime/'jobs').glob('*.json'):
        job=read(path)
        if job.get('status') in ('pending','running'):
            record(path,'Tarea pendiente o en curso',protected);notes.append('Hay tareas activas: no ejecutar ninguna limpieza.');continue
        last=job.get('finished_at') or job.get('created_at')
        age=now-datetime.fromisoformat(last.replace('Z','+00:00')).timestamp() if last else 0
        old=age>=policy['job_log_days']*86400
        record(path,'Registro de tarea terminado y anterior al plazo' if old else 'Registro de tarea reciente',candidates if old else protected)
    # Solo formatos temporales conocidos de los dos motores; no recorrer todo runtime.
    temps=list(snapshots.glob('.building-*'))
    for _,cache,_ in caches: temps.extend(list(cache.glob('*/image.tmp'))+list(cache.glob('*/metadata.tmp')))
    for path in temps:
        old=now-newest(path)>=policy['temporary_hours']*3600
        record(path,'Temporal antiguo; verificar que ninguna tarea lo utiliza' if old else 'Temporal reciente',candidates if old else protected)
    return {'mode':'dry_run','generated_at_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
        'policy':policy,'candidates':candidates,'protected':protected,'candidate_bytes':sum(p['bytes'] for p in candidates),
        'notes':list(set(notes))+['Inventario sin eliminación. Revalidar referencias y tareas antes de ejecutar cualquier limpieza.'],
        'preserved':['Histórico INAB y detecciones activas','Originales','Respaldos','Caché EUMETSAT','Archivos de validación','Entorno Conda']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).resolve().parent.parent/'config.yaml')
    args=parser.parse_args();project=args.config.resolve().parent;config=yaml.safe_load(args.config.read_text())
    report=plan(project,config);target=(project/config['retention']['report']).resolve()
    if not target.is_relative_to(project/'runtime/retention'): raise ValueError('Informe fuera de runtime/retention')
    target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.tmp');temp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');temp.replace(target)
    print(f"Simulación: {len(report['candidates'])} candidatos; {report['candidate_bytes']/1024**2:.2f} MiB recuperables. No se eliminó ningún archivo.")
    print('Informe:',target.relative_to(project))
if __name__=='__main__':main()
