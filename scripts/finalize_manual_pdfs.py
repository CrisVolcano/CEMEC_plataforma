"""Conserva navegación y enlaces al publicar los PDF renderizados de los manuales.

La conversión de LibreOffice local conserva marcadores pero no anotaciones de
hipervínculo. Se añaden sin modificar el contenido visual de las páginas.
"""
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree
import pdfplumber
from pypdf import PdfReader,PdfWriter
from pypdf.annotations import Link
from pypdf.generic import Fit

ROOT=Path(__file__).resolve().parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def outline_destinations(reader,items):
    found={}
    for item in items:
        if isinstance(item,list):found.update(outline_destinations(reader,item))
        else:found[str(item['/Title'])]=(reader.get_destination_page_number(item),float(item.get('/Top',792)))
    return found

def finish(kind):
    stem='manual-'+kind;source=ROOT/'runtime/manuales-qa'/kind/(stem+'.pdf')
    target=ROOT/'docs/manuales'/(stem+'.pdf');reader=PdfReader(source);writer=PdfWriter(clone_from=reader)
    with ZipFile(ROOT/'docs/manuales'/(stem+'.docx')) as z:
        rels=etree.fromstring(z.read('word/_rels/document.xml.rels'))
        urls={e.get('Id'):e.get('Target') for e in rels}
        xml=etree.fromstring(z.read('word/document.xml'))
        external=[(''.join(e.xpath('.//w:t/text()',namespaces=NS)),urls[e.get('{'+NS['r']+'}id')]) for e in xml.xpath('//w:hyperlink[@r:id]',namespaces=NS)]
    dest=outline_destinations(reader,reader.outline);count=0
    with pdfplumber.open(source) as pdf:
        titles=re.findall(r'^## (.+)$',(ROOT/'docs/manuales'/(stem+'.md')).read_text(),re.M)
        for title in titles:
            matches=pdf.pages[1].search(re.escape(title));assert matches,('Índice sin destino',title)
            page_index,top=dest[title]
            for hit in matches:
                rect=(hit['x0'],pdf.pages[1].height-hit['bottom'],hit['x1'],pdf.pages[1].height-hit['top'])
                writer.add_annotation(1,Link(rect=rect,target_page_index=page_index,fit=Fit.xyz(left=0,top=top,zoom=0)));count+=1
        # Cada texto repetido conserva el destino de su aparición en el Word.
        candidates={};used={}
        for label,url in external:
            if label not in candidates:
                candidates[label]=[(i,hit) for i,page in enumerate(pdf.pages) for hit in page.search(r'\s*'.join(re.escape(ch) for ch in label))]
            index=used.get(label,0);assert index<len(candidates[label]),('Enlace sin texto',label,url)
            page_index,hit=candidates[label][index];used[label]=index+1;page=pdf.pages[page_index]
            rect=(hit['x0'],page.height-hit['bottom'],hit['x1'],page.height-hit['top'])
            writer.add_annotation(page_index,Link(rect=rect,url=url));count+=1
    writer.write(target)
    result=PdfReader(target);assert len(result.pages)==len(reader.pages)
    assert [p.extract_text() for p in result.pages]==[p.extract_text() for p in reader.pages]
    print(stem,len(result.pages),'páginas',count,'enlaces activos')
if __name__=='__main__':
    finish('instalacion');finish('uso')
