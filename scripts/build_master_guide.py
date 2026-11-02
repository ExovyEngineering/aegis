"""Build the printable user handbook from reviewed chapters and dated evidence.

Uses the project's existing matplotlib/pypdf dependencies. No provider request,
operational database access, browser installation or new PDF service is needed.
"""
import argparse
from datetime import datetime
from functools import lru_cache
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PARTS = (
    'docs/manual_parts/start.md', 'docs/manual_parts/operations.md',
    'docs/manual_parts/freshness.md',
    'docs/manual_parts/dispatch_drive.md', 'docs/manual_parts/evidence_science.md',
    'docs/manual_parts/assistant.md', 'docs/manual_parts/rehearsal.md',
    'docs/recording_guide.md', 'docs/manual_parts/reference.md',
)
TITLE = 'AEGIS Master User Guide'


def plain(value):
    def link(match):
        label, target = match.groups()
        return label if target.startswith('#') else f'{label} ({target})'
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, value)
    return re.sub(r'\*\*([^*]+)\*\*|`([^`]+)`', lambda m: m[1] or m[2], value).replace('\\|', '|')


def inline(value):
    """Escape first; only our bounded inline Markdown produces HTML elements."""
    value = html.escape(value)
    def link(match):
        label, target = match.groups()
        if target.startswith(('https://', 'http://', '#')):
            return f'<a href="{target}">{label}</a>'
        return f'{label} (<code>{target}</code>)'
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', value).replace('\\|', '|')


def parse_markdown(body):
    lines = body.splitlines(); blocks = []; position = 0; used = {}
    while position < len(lines):
        line = lines[position]
        if not line.strip():
            position += 1; continue
        heading = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading:
            title = heading[2]
            slug = re.sub(r'[^a-z0-9]+', '-', plain(title).lower()).strip('-') or 'section'
            used[slug] = used.get(slug, 0) + 1
            blocks.append({'kind':'heading', 'level':len(heading[1]), 'text':title,
                           'id':slug if used[slug] == 1 else f'{slug}-{used[slug]}'})
            position += 1; continue
        if line.startswith('```'):
            position += 1; code = []
            while position < len(lines) and not lines[position].startswith('```'):
                code.append(lines[position]); position += 1
            if position == len(lines):
                raise ValueError('Unclosed code fence in master-guide source')
            blocks.append({'kind':'code', 'lines':code}); position += 1; continue
        if line.lstrip().startswith('|'):
            rows = []
            while position < len(lines) and lines[position].lstrip().startswith('|'):
                cells = lines[position].strip().strip('|').replace('\\|', '\x00').split('|')
                cells = [cell.strip().replace('\x00', '\\|') for cell in cells]
                if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                    rows.append(cells)
                position += 1
            if not rows or any(len(row) != len(rows[0]) for row in rows):
                raise ValueError('Master-guide table has inconsistent column counts')
            blocks.append({'kind':'table', 'rows':rows}); continue
        item = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)$', line)
        if item:
            text = item[3]; position += 1
            while position < len(lines) and lines[position].startswith('  ') and lines[position].strip() and not re.match(r'^\s*([-*]|\d+\.)\s+', lines[position]):
                text += ' ' + lines[position].strip(); position += 1
            blocks.append({'kind':'item', 'text':text, 'marker':'•' if item[2] in ('-', '*') else item[2],
                           'indent':min(24, len(item[1]) * 3)})
            continue
        text = line.strip(); position += 1
        while position < len(lines) and lines[position].strip() and not re.match(r'^(#{1,4}\s|\s*[-*]\s|\s*\d+\.\s|\s*\||```)', lines[position]):
            text += ' ' + lines[position].strip(); position += 1
        blocks.append({'kind':'paragraph', 'text':text})
    return blocks


def evidence_chapter(root):
    path = root / 'reports/session_verification.json'
    checks = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    body = ['## Recorded verification and what remains open', '',
            'A saved pass describes an executed check at its recorded time. It is not a promise that every provider is online now, that a vehicle is safe, or that the submission has been approved.', '',
            f"Latest saved local check finished: {checks.get('finished_at', 'not recorded')}. Read the following results literally; missing evidence is not counted as a pass.", '',
            '| Check | Saved result | Meaning |', '| --- | --- | --- |']
    for row in checks.get('checks', []):
        result = 'PASS' if row.get('passed') else 'FAIL'
        count = row.get('tests_passed')
        body.append(f"| {row['name']} | {result}{f'; {count} tests' if count is not None else ''} | Executed local command; see {row.get('log', 'recorded log')} |")
    if not checks.get('checks'):
        body.append('| Local suite | Not recorded | Run the documented checks; no result inferred |')
    body += ['', 'Backend tests exercise data handling, holds, recalls, capacities, eligibility, approvals, stale versions, driver safeguards and isolated rehearsal. Frontend tests exercise user interactions and error states. A production build checks that the app compiles. These cover different questions.', '']
    for folder, label in [('recording','Recording preparation: Chrome workflows and automated tracker record'), ('freshness','Save the Load, FEFO and driver handoff'), ('roads','Road intelligence'), ('rehearsal','Guided rehearsal'),
                          ('readiness','County context/readiness'), ('drive','Drive'),
                          ('operations','Dispatcher/custom operations'), ('depth','Planning/evidence depth'),
                          ('controls','Command controls')]:
        path = root / f'reports/browser_qa/{folder}/results.json'
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8')); rows = value.get('checks', [])
            passed = sum(bool(row.get('passed')) for row in rows)
            body.append(f"- {label}: {passed}/{len(rows)} saved browser checks, recorded {value.get('checked_at', 'at the timestamp in its artifact')}. Evidence: reports/browser_qa/{folder}/results.json. Runs have separate dates and are not all repeated for every change.")
    friendly=root/'reports/friendliness_workflow_evaluation.json'
    if friendly.is_file():
        value=json.loads(friendly.read_text(encoding='utf-8'));rows=value.get('checks',[])
        body += ['', f"The guided delivery-outlook, chicken-question, map-layer, road and dispatcher walkthrough recorded {sum(bool(row.get('passed')) for row in rows)}/{len(rows)} actual-Chrome checks at {value.get('checked_at','the artifact timestamp')}. External map tiles used browser-only QA placeholders; no public providers or language model were queried. This verifies application behavior, not prospective prediction accuracy. Evidence: reports/friendliness_workflow_evaluation.json."]
    replay=root/'reports/freshness_demo.json'
    if replay.is_file():
        value=json.loads(replay.read_text(encoding='utf-8'));rows=value.get('checks',[])
        body += ['', f"The accelerated deterministic freshness replay recorded {sum(bool(row.get('passed')) for row in rows)}/{len(rows)} checks. Evidence: reports/freshness_demo.json. It uses a fresh isolated database and simulated sensor packets; no physical hardware, calibrated spoilage prediction or timed human presentation is inferred."]
    body += ['', 'The reviewer-package check verifies paths and checksums, extracts trusted project code into a separate directory, blocks application networking, and exercises offline workflows. It does not establish a new dependency installation unless a separate installation report explicitly records one.', '',
             'A deliberately injected browser failure is a test case, not a provider outage. A test failure and its correction remain part of the evidence history. The earlier duplicate CI timing failure and synchronized follow-up are described in reports/ci_followup.json. For the current remote commit, inspect GitHub checks directly rather than assuming an older run applies.', '',
             '### Submission and scientific gates still requiring real evidence', '',
             '- Genuine Kiro sign-in, specification execution and reviewed task/test evidence remain separate from Codex-generated files or an installed IDE.',
             '- Final organizer-rubric review, author review and a timed human team presentation remain pending unless the team records their actual completion.',
             '- Actual per-result public availability dates are missing. Retrospective sampling results are not a validated prospective forecast.',
             '- NOAA coverage is bounded and retains precipitation gaps; no validated FSIS-weather join is claimed.',
             '- Isolate-level genomic linkage, production accounts, physical sensors, cloud hosting and evaluated language-model advice are not implemented. The evidence assistant uses server-authored facts; optional topic selection is not a validated advisory model.', '',
             'Use the application to explain a transparent decision-support workflow and measured limitations. Do not replace an open requirement with a feature count or an invented accuracy figure.']
    return '\n'.join(body)


def html_document(blocks, generated, title=TITLE):
    toc = [block for block in blocks if block['kind'] == 'heading' and block['level'] == 2]
    parts = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>',
        'body{font:16px/1.55 Georgia,serif;color:#18251e;background:#f0f2ed;margin:0}main{max-width:900px;margin:auto;background:white;padding:44px}h1,h2,h3,h4,nav,button{font-family:Arial,sans-serif}h1{font-size:38px}h2{margin-top:48px;border-bottom:2px solid #345b46;padding-bottom:10px}h3{margin-top:28px}a{color:#25593e}table{width:100%;border-collapse:collapse;font:14px/1.5 Arial,sans-serif;margin:18px 0}th,td{text-align:left;vertical-align:top;padding:10px;border:1px solid #bcc7bc;overflow-wrap:anywhere}th{background:#eef2eb}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5ef;padding:14px;font-size:13px}code{font-size:.9em;overflow-wrap:anywhere}li{margin:8px 0}nav{border:1px solid #ccd6ca;padding:20px}nav ol{columns:2;column-gap:30px}nav li{break-inside:avoid}button{padding:12px 18px;background:#23543c;color:white;border:0;border-radius:5px;cursor:pointer}.stamp{color:#526151}.cover-note{border-left:4px solid #426b50;padding-left:18px}.document-footer{margin-top:40px;border-top:1px solid #bbc5b9;padding-top:14px;font-size:13px}@page{size:letter;margin:.65in}@media print{body{background:white;font-size:11pt;line-height:1.45}main{padding:0;max-width:none}button,.screen-only{display:none}h2{break-before:page;margin-top:0;font-size:19pt}h3,h4{break-after:avoid}table{font-size:9.5pt}thead{display:table-header-group}tr{break-inside:avoid}pre{break-inside:avoid}a{color:inherit;text-decoration:none}nav ol{columns:1}p,li{orphans:3;widows:3}}@media(max-width:650px){main{padding:20px}nav ol{columns:1}table{font-size:12px}th,td{padding:6px}}',
        '</style></head><body><main>', f'<h1>{title}</h1><p class="stamp">Generated {html.escape(generated)}. Complete user handbook; local research demonstrator.</p>',
        '<p class="cover-note">For teammates learning the product and preparing a presentation. Real public evidence, simulated logistics, planning estimates and unfinished capabilities are identified separately.</p>',
        '<button type="button" onclick="window.print()">Print this guide</button><p class="screen-only">Print on US Letter paper. The PDF version includes page numbers, a page-numbered contents list and bookmarks. This standalone HTML uses no external fonts, images or scripts.</p>',
        '<nav aria-label="Guide contents"><strong>Contents</strong><ol>' + ''.join(f'<li><a href="#{row["id"]}">{inline(row["text"])}</a></li>' for row in toc) + '</ol></nav>']
    for block in blocks:
        kind = block['kind']
        if kind == 'heading':
            level = block['level']; parts.append(f'<h{level} id="{block["id"]}">{inline(block["text"])}</h{level}>')
        elif kind == 'paragraph':parts.append('<p>' + inline(block['text']) + '</p>')
        elif kind == 'item':parts.append('<p class="list-item">' + html.escape(block['marker']) + ' ' + inline(block['text']) + '</p>')
        elif kind == 'code':parts.append('<pre><code>' + html.escape('\n'.join(block['lines'])) + '</code></pre>')
        elif kind == 'image':
            import base64
            encoded=base64.b64encode(block['bytes']).decode('ascii')
            parts.append('<figure><img style="max-width:100%;height:auto" alt="'+html.escape(block.get('caption','System diagram'))+'" src="data:image/png;base64,'+encoded+'"><figcaption>'+inline(block.get('caption',''))+'</figcaption></figure>')
        elif kind == 'table':
            rows = block['rows'];parts.append('<table><thead><tr>' + ''.join('<th>'+inline(cell)+'</th>' for cell in rows[0]) + '</tr></thead><tbody>')
            parts += ['<tr>' + ''.join('<td>'+inline(cell)+'</td>' for cell in row) + '</tr>' for row in rows[1:]]
            parts.append('</tbody></table>')
    parts.append('<p class="document-footer">AEGIS • Master user guide • Simulated operations; dated evidence; human review. Use the current application labels and source timestamps when presenting.</p></main></body></html>')
    return '\n'.join(parts)


def render_pdf(blocks, output, generated, preview_dir=None, title=TITLE, cover_subtitle="Master User Guide", preview_all=False,
               cover_sections=None, cover_label='Read, practice, present', subject='Complete product handbook, controls, use cases and limitations'):
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.font_manager import FontProperties
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    from matplotlib.textpath import TextToPath
    from pypdf import PdfReader, PdfWriter
    from pypdf.annotations import Link

    width, height = 612, 792  # US Letter, in PDF points.
    left, right, top, bottom = 47, 565, 733, 56
    measure = TextToPath()

    @lru_cache(maxsize=20000)
    def text_width(value, size, weight='normal', mono=False):
        font = FontProperties(family='DejaVu Sans Mono' if mono else 'DejaVu Sans', size=size, weight=weight)
        return measure.get_text_width_height_descent(value, font, ismath=False)[0]

    def wrap(value, maximum, size=10.7, weight='normal', mono=False):
        output_lines=[]; current=''
        for word in plain(value).split():
            candidate = (current + ' ' + word).strip()
            if text_width(candidate, size, weight, mono) <= maximum:
                current=candidate;continue
            if current:output_lines.append(current);current=''
            while text_width(word, size, weight, mono) > maximum:
                length=max(1,int(len(word)*maximum/text_width(word,size,weight,mono)))
                while text_width(word[:length],size,weight,mono)>maximum:length-=1
                output_lines.append(word[:length]);word=word[length:]
            current=word
        if current:output_lines.append(current)
        return output_lines or ['']

    pages=[]; page=None; y=top; current_chapter='User handbook'; chapter_pages=[]; headings=[]; overflow=[]
    def new_page():
        nonlocal page,y
        page=[];pages.append({'chapter':current_chapter,'items':page});y=top
    def text(value,x,baseline,size=10.7,weight='normal',mono=False):
        extent=text_width(value,size,weight,mono)
        if x < left-.1 or x+extent > right+.2 or baseline < bottom or baseline > top+1:
            overflow.append({'text':value,'x':x,'y':baseline,'width':extent})
        page.append(('text',value,x,baseline,size,weight,mono))
    def paragraph(value, *, size=10.7, weight='normal', indent=0, gap=8, mono=False, prefix=''):
        nonlocal y
        lines=wrap(value,right-left-indent-(18 if prefix else 0),size,weight,mono)
        leading=size*1.38
        if y-leading*min(2,len(lines)) < bottom:new_page()
        for index,line in enumerate(lines):
            if y < bottom+leading:new_page()
            if index==0 and prefix:text(prefix,left+indent,y,size,weight,mono)
            text(line,left+indent+(18 if prefix else 0),y,size,weight,mono);y-=leading
        y-=gap
    new_page()
    for block in blocks:
        kind=block['kind']
        if kind=='heading':
            level=block['level']
            if level==2:
                current_chapter=plain(block['text'])
                if page:new_page()
                pages[-1]['chapter']=current_chapter
                chapter_pages.append({'id':block['id'],'title':current_chapter,'body_page_index':len(pages)-1})
            elif y<bottom+85:new_page()
            headings.append({'title':plain(block['text']),'body_page_index':len(pages)-1,'level':level})
            paragraph(block['text'],size=17 if level==2 else 12.5 if level==3 else 11.3,weight='bold',gap=13)
        elif kind=='paragraph':paragraph(block['text'])
        elif kind=='image':
            import io
            from matplotlib.image import imread
            pixels=imread(io.BytesIO(block['bytes']),format='png')
            image_height=(right-left)*pixels.shape[0]/pixels.shape[1]
            if image_height>top-bottom-35:raise ValueError('Diagram too tall for the print layout')
            if y-image_height<bottom+20:new_page()
            page.append(('image',pixels,left,y-image_height,right-left,image_height));y-=image_height+12
            if block.get('caption'):paragraph(block['caption'],size=9.3)
        elif kind=='item':paragraph(block['text'],indent=block['indent'],prefix=block['marker'],gap=5)
        elif kind=='code':
            for line in block['lines']:paragraph(line or ' ',size=9.2,mono=True,gap=3,indent=8)
            y-=6
        elif kind=='table':
            rows=block['rows']; columns=len(rows[0]); widths=[(right-left)/columns]*columns
            # Give explanatory text more space than short control names.
            if columns==3:widths=[125,185,right-left-310]
            if columns==2:widths=[170,right-left-170]
            size=9.7;leading=13.4;padding=7
            def row_height(row):return max(len(wrap(cell,space-2*padding,size)) for cell,space in zip(row,widths))*leading+2*padding
            def draw_row(row,header=False):
                nonlocal y
                wrapped=[wrap(cell,space-2*padding,size,'bold' if header else 'normal') for cell,space in zip(row,widths)]
                extent=max(map(len,wrapped))*leading+2*padding
                if extent>top-bottom-50:raise ValueError('Guide table row too tall to print; split its source text')
                x=left
                for lines,space in zip(wrapped,widths):
                    page.append(('rect',x,y-extent+3,space,extent,header))
                    for index,line in enumerate(lines):text(line,x+padding,y-padding-index*leading,size,'bold' if header else 'normal')
                    x+=space
                y-=extent
            header_height=row_height(rows[0])
            if y<header_height+bottom+45:new_page()
            draw_row(rows[0],True)
            for row in rows[1:]:
                if y-row_height(row)<bottom+8:new_page();draw_row(rows[0],True)
                draw_row(row)
            y-=13
    if overflow:raise ValueError(f'Master guide text exceeds print margins: {overflow[:2]}')

    # Contents pagination is calculated before final absolute page numbers.
    toc_pages=[[]];toc_y=686
    for chapter in chapter_pages:
        lines=wrap(chapter['title'],right-left-45,11)
        if toc_y-len(lines)*16<90:toc_pages.append([]);toc_y=686
        toc_pages[-1].append((chapter,lines,toc_y));toc_y-=len(lines)*16+9
    offset=1+len(toc_pages); total=offset+len(pages); links=[]
    for chapter in chapter_pages:chapter['page']=offset+chapter['body_page_index']+1
    preview_pages={1,2,8,14,21,27,28,29,35,44,59,total}
    for chapter in chapter_pages:
        if chapter['id']=='record-the-final-video':
            preview_pages.update(range(chapter['page'],min(chapter['page']+3,total+1)))

    def figure(number,chapter):
        fig=Figure(figsize=(8.5,11),facecolor='white')
        fig.text(left/width,762/height,title.upper(),fontsize=8.5,color='#333333',family='DejaVu Sans')
        fig.text(right/width,762/height,chapter[:74],fontsize=7.5,color='#555555',ha='right',family='DejaVu Sans')
        fig.text(left/width,27/height,'Local research demonstrator | Source and simulation labels matter',fontsize=7.5,color='#444444')
        fig.text(right/width,27/height,f'{number} / {total}',fontsize=8.5,ha='right')
        return fig
    def save_page(pdf,fig,number):
        pdf.savefig(fig)
        if preview_dir is not None and (preview_all or number in preview_pages):
            preview_dir.mkdir(parents=True,exist_ok=True)
            fig.savefig(preview_dir/f'print-render-page-{number:02}.png',dpi=120)
    with PdfPages(output,metadata={'Title':title,'Author':'AEGIS project team','Subject':subject}) as pdf:
        fig=figure(1,cover_label)
        fig.text(left/width,.79,'AEGIS',fontsize=44,weight='bold',color='#173c2b')
        fig.text(left/width,.725,cover_subtitle,fontsize=27,weight='bold')
        fig.text(left/width,.667,'Command • Drive • Evidence • Science',fontsize=14)
        cover=cover_sections if cover_sections is not None else [('What this is','A printable explanation of everything currently available in the application, with control references and practical use cases.'),
               ('Who it is for','Teammates, presenters, reviewers and anyone learning how the parts connect.'),
               ('How to read it','Start with the orientation and choose a use case. Use the contents, PDF bookmarks and glossary when you return.'),
               ('Keep the boundaries clear','Public evidence is distinct from simulated operations. Forecasts, estimates, historical observations and cargo projections are labeled separately.')]
        cover_y=.59
        for label,value in cover:
            fig.text(left/width,cover_y,label,fontsize=12,weight='bold');cover_y-=.027
            lines=wrap(value,right-left,11)
            fig.text(left/width,cover_y,'\n'.join(lines),fontsize=11,va='top',linespacing=1.45);cover_y-=len(lines)*.021+.035
        fig.text(left/width,.115,f'Generated {generated}',fontsize=9)
        fig.text(left/width,.085,'US Letter • 100% scale • grayscale-friendly • duplex optional',fontsize=9)
        save_page(pdf,fig,1)
        for index,entries in enumerate(toc_pages):
            fig=figure(index+2,'Contents')
            fig.text(left/width,720/height,'Contents',fontsize=23,weight='bold')
            for chapter,lines,baseline in entries:
                fig.text(left/width,baseline/height,'\n'.join(lines),fontsize=11,va='baseline',linespacing=1.45)
                fig.text(right/width,baseline/height,str(chapter['page']),fontsize=11,ha='right')
                links.append((index+1,(left,baseline-len(lines)*16+3,right,baseline+13),chapter['page']-1))
            save_page(pdf,fig,index+2)
        for index,content in enumerate(pages):
            fig=figure(offset+index+1,content['chapter'])
            for item in content['items']:
                if item[0]=='text':
                    _,value,x,baseline,size,weight,mono=item
                    fig.text(x/width,baseline/height,value,fontsize=size,weight=weight,family='DejaVu Sans Mono' if mono else 'DejaVu Sans',va='baseline',parse_math=False)
                elif item[0]=='image':
                    _,pixels,x,baseline,space,extent=item
                    axes=fig.add_axes((x/width,baseline/height,space/width,extent/height));axes.imshow(pixels);axes.axis('off')
                else:
                    _,x,baseline,space,extent,header=item
                    fig.add_artist(Rectangle((x/width,baseline/height),space/width,extent/height,transform=fig.transFigure,facecolor='#eeeeee' if header else 'white',edgecolor='#b0b0b0',linewidth=.55,zorder=-1))
            save_page(pdf,fig,offset+index+1)
    reader=PdfReader(output);writer=PdfWriter();writer.append_pages_from_reader(reader)
    writer.add_metadata({'/Title':title,'/Author':'AEGIS project team','/Subject':'Product controls, practical use cases and scientific boundaries'})
    for chapter in chapter_pages:writer.add_outline_item(chapter['title'],chapter['page']-1)
    for source,rectangle,target in links:writer.add_annotation(source,Link(rect=rectangle,target_page_index=target,border=[0,0,0]))
    with tempfile.NamedTemporaryFile(dir=output.parent,suffix='.pdf',delete=False) as stream:
        temporary=Path(stream.name);writer.write(stream)
    try:os.replace(temporary,output)
    finally:
        if temporary.exists():temporary.unlink()
    return {'pages':total,'chapters':chapter_pages,'overflow_count':len(overflow),'paper':'US Letter',
            'body_font_points':10.7,'table_font_points':9.7,'bookmarks':len(chapter_pages),'contents_links':len(links)}


def build(root=ROOT,preview_dir=None):
    root=Path(root);sources=[];chapters=[]
    for name in PARTS:
        path=root/name
        if not path.is_file():raise ValueError(f'Master guide source chapter missing: {name}')
        body=path.read_text(encoding='utf-8')
        sources.append({'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});chapters.append(body.strip())
    generated=datetime.now(ZoneInfo('America/Chicago')).strftime('%B %d, %Y at %I:%M %p CT')
    body='\n\n'.join([*chapters,evidence_chapter(root)])+'\n'
    blocks=parse_markdown(body)
    if not any(row['kind']=='heading' and row['level']==2 for row in blocks):raise ValueError('Master guide needs chapter headings')
    reports=root/'reports';reports.mkdir(parents=True,exist_ok=True)
    markdown=root/'docs/aegis_master_guide.md'
    markdown.write_text(f'# {TITLE}\n\nGenerated {generated}. Complete product handbook.\n\nThis master file is assembled from docs/manual_parts/ and dated reports. Edit those sources and rebuild to keep PDF, HTML and Markdown consistent.\n\n'+body,encoding='utf-8')
    html_path=reports/'aegis_master_guide.html';html_path.write_text(html_document(blocks,generated),encoding='utf-8')
    pdf=reports/'aegis_master_guide.pdf';layout=render_pdf(blocks,pdf,generated,Path(preview_dir) if preview_dir else None)
    artifact={'generated_at':datetime.now(ZoneInfo('America/Chicago')).isoformat(),'title':TITLE,
              'pdf':pdf.relative_to(root).as_posix(),'markdown':markdown.relative_to(root).as_posix(),
              'html':html_path.relative_to(root).as_posix(),'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
              'bytes':pdf.stat().st_size,**layout,'source_files':sources,
              'verification_snapshot':'reports/session_verification.json','live_api_requests_performed':False,
              'operational_database_accessed':False}
    (reports/'master_guide_manifest.json').write_text(json.dumps(artifact,indent=2)+'\n',encoding='utf-8')
    return artifact


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir',type=Path,help='Optional native print-render PNG previews for document layout review')
    args=parser.parse_args()
    print(json.dumps(build(preview_dir=args.preview_dir),indent=2))
