"""Construye los dos manuales Word desde sus fuentes Markdown.

Herramienta editorial opcional: requiere python-docx y Pillow, no el backend.
PDF y PNG de verificación se obtienen mediante el renderizador documental.
"""
from pathlib import Path
import re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/manuales'
BLACK=RGBColor(0,0,0)

def field(p,instruction):
    r=OxmlElement('w:r');f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),instruction)
    t=OxmlElement('w:t');t.text='1';r.append(t);f.append(r);p._p.append(f)

def link(p,text,url=None,anchor=None):
    h=OxmlElement('w:hyperlink')
    if anchor:h.set(qn('w:anchor'),anchor)
    else:h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    c=OxmlElement('w:color');c.set(qn('w:val'),'245B47');pr.append(c)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u);r.append(pr)
    t=OxmlElement('w:t');t.text=text;r.append(t);h.append(r);p._p.append(h)

def inline(p,text):
    # El Markdown es la fuente completa; los enlaces largos tienen etiqueta legible en Word.
    parts=re.split(r'(https?://\S+|\*\*.+?\*\*|`[^`]+`)',text)
    for part in parts:
        if part.startswith('http'):
            stripped=part.rstrip('.,;')
            link(p,'Abrir enlace oficial' if len(stripped)>78 else stripped,url=stripped)
            if len(stripped)!=len(part):p.add_run(part[len(stripped):])
        elif part.startswith('**'):p.add_run(part[2:-2]).bold=True
        elif part.startswith('`'):
            r=p.add_run(part[1:-1]);r.font.name='DejaVu Sans Mono';r.font.size=Pt(9)
        else:p.add_run(part)

def style_document(doc,label):
    sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
    sec.top_margin=sec.bottom_margin=Inches(.78);sec.left_margin=sec.right_margin=Inches(.8)
    sec.footer_distance=Inches(.35)
    for style in doc.styles:
        for border in list(style.element.xpath('.//w:pBdr')):border.getparent().remove(border)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(11);normal.font.color.rgb=BLACK
    normal.paragraph_format.line_spacing=1.06;normal.paragraph_format.space_after=Pt(5)
    normal.paragraph_format.keep_together=True
    for name,size in [('Title',26),('Subtitle',13),('Heading 1',17),('Heading 2',12.5),('Heading 3',11.5)]:
        st=doc.styles[name];st.font.name='Calibri';st.font.size=Pt(size);st.font.color.rgb=BLACK
        st.paragraph_format.space_before=Pt(15 if name.startswith('Heading') else 0)
        st.paragraph_format.space_after=Pt(7)
        if name.startswith('Heading'):st.font.bold=True;st.paragraph_format.keep_with_next=True
        for e in list(st.element.xpath('.//w:color')):e.attrib.pop(qn('w:themeColor'),None)
    for name in ('List Bullet','List Number'):
        doc.styles[name].font.name='Calibri';doc.styles[name].font.size=Pt(11)
        doc.styles[name].paragraph_format.space_after=Pt(5)
    # El estilo Code conserva texto copiable; el fondo se limita a código, no a resúmenes.
    from docx.enum.style import WD_STYLE_TYPE
    code=doc.styles.add_style('Code',WD_STYLE_TYPE.PARAGRAPH);code.font.name='DejaVu Sans Mono';code.font.size=Pt(8.6)
    code.paragraph_format.line_spacing=1.03;code.paragraph_format.space_after=Pt(2)
    code.paragraph_format.left_indent=Inches(.12);code.paragraph_format.right_indent=Inches(.06)
    caption=doc.styles['Caption'];caption.font.name='Calibri';caption.font.size=Pt(10);caption.font.color.rgb=BLACK;caption.font.bold=False;caption.font.italic=False
    caption.paragraph_format.space_after=Pt(9)
    sec.different_first_page_header_footer=True
    f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=f.add_run('CEMEC  |  '+label+'  |  ');r.font.size=Pt(9);field(f,'PAGE')
    doc.core_properties.title='CEMEC '+label
    doc.core_properties.subject='Manual de la plataforma CEMEC'
    doc.core_properties.author='Documentación del proyecto'
    doc.core_properties.keywords='CEMEC, manual, Windows, WSL2, FIRMS, EUMETSAT, CDSE'
    lang=OxmlElement('w:lang');lang.set(qn('w:val'),'es-GT');doc.styles['Normal'].element.get_or_add_rPr().append(lang)


def make_table(doc,rows):
    n=len(rows[0]);t=doc.add_table(rows=1,cols=n);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    borders=OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        border=OxmlElement('w:'+edge);border.set(qn('w:val'),'single');border.set(qn('w:sz'),'4');border.set(qn('w:color'),'D9D9D9');borders.append(border)
    t._tbl.tblPr.append(borders)
    if n==2:widths=[2.8,4.1] if rows[0][0]=='Ruta de configuración' else [2.15,4.75]
    elif n==4:widths=[1.12,1.65,1.55,2.58]
    else:widths=[6.9/n]*n
    for c,w in zip(t.columns,widths):c.width=Inches(w)
    for i,row in enumerate(rows):
        cells=t.rows[0].cells if i==0 else t.add_row().cells
        for j,(cell,text) in enumerate(zip(cells,row)):
            cell.width=Inches(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3);p.paragraph_format.line_spacing=1.08
            inline(p,text)
            for r in p.runs:r.font.size=Pt(10)
            pr=cell._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for side in ('top','left','bottom','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'85');e.set(qn('w:type'),'dxa');m.append(e)
            pr.append(m)
            if i==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E7EEF5');pr.append(sh)
                for r in p.runs:r.bold=True;r.font.color.rgb=BLACK
        tr=t.rows[i]._tr.get_or_add_trPr();keep=OxmlElement('w:cantSplit');tr.append(keep)
        if i==0:tr.append(OxmlElement('w:tblHeader'))
    doc.add_paragraph().paragraph_format.space_after=Pt(2)
    return t

def build(stem,label):
    lines=(OUT/(stem+'.md')).read_text().splitlines();doc=Document();style_document(doc,label)
    first=next(i for i,l in enumerate(lines) if l.startswith('## '));front=[l for l in lines[1:first] if l.strip()]
    doc.add_paragraph('CEMEC',style='Subtitle')
    doc.add_paragraph(lines[0][2:],style='Title')
    for i,text in enumerate(front):
        p=doc.add_paragraph(style='Subtitle' if i==0 else None);inline(p,text)
    doc.add_page_break()
    doc.add_paragraph('Contenido',style='Heading 1')
    chapters=[l[3:] for l in lines if l.startswith('## ')]
    for i,title in enumerate(chapters):
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(6);link(p,title,anchor='chapter_'+str(i+1))
    doc.add_paragraph('Los títulos del índice son enlaces. En Word también puede utilizar el panel de navegación.',style='Caption')
    doc.add_page_break();i=first;chapter=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('## '):
            chapter+=1;p=doc.add_paragraph(line[3:],style='Heading 1')
            start=OxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(chapter));start.set(qn('w:name'),'chapter_'+str(chapter))
            stop=OxmlElement('w:bookmarkEnd');stop.set(qn('w:id'),str(chapter));p._p.insert(0,start);p._p.append(stop)
        elif line.startswith('### '):doc.add_paragraph(line[4:],style='Heading 2')
        elif line.startswith('```'):
            lang=line[3:];p=doc.add_paragraph('Terminal '+({'bash':'Ubuntu','powershell':'PowerShell de Windows','cmd':'Miniforge Prompt de Windows','dotenv':'Archivo .env'}.get(lang,lang)),style='Caption');p.paragraph_format.keep_with_next=True
            i+=1;block=[]
            while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
            p=doc.add_paragraph('\n'.join(block),style='Code');p.paragraph_format.keep_together=True
            doc.add_paragraph().paragraph_format.space_after=Pt(2)
        elif line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[c.strip() for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[: -]+',c) for c in cells):rows.append(cells)
                i+=1
            make_table(doc,rows);continue
        elif line.startswith('!['):
            m=re.match(r'!\[(.*?)\]\((.*?)\)',line);image=OUT/m[2]
            p=doc.add_paragraph();p.paragraph_format.keep_with_next=True
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            run=p.add_run();inline_pic=run.add_picture(str(image),width=Inches(3.4 if '02-capas' in image.name else 6.0 if '03-detalle' in image.name else 6.9))
            inline_pic._inline.docPr.set('descr',m[1])
            doc.add_paragraph(m[1],style='Caption')
        elif line.startswith('- '):inline(doc.add_paragraph(style='List Bullet'),line[2:])
        elif re.match(r'^\d+\. ',line):
            # Numeración explícita para reiniciar cada procedimiento con fiabilidad.
            p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.18);p.paragraph_format.first_line_indent=Inches(-.18);inline(p,line)
        else:inline(doc.add_paragraph(),line)
        i+=1
    doc.save(OUT/(stem+'.docx'))
    print(stem, len(chapters),'capítulos')

if __name__=='__main__':
    build('manual-instalacion','Instalación y configuración')
    build('manual-uso','Uso e interpretación')
