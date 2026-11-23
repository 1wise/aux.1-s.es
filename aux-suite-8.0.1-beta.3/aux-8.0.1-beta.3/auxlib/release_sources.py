# Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Read the official NixOS channel table without guessing a revision URL."""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit


class ReleaseTable(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.cells=[];self.cell=None;self.href=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.cells=[];self.href=None
        if tag=='td':self.cell=''
        if tag=='a' and self.cell is not None:self.href=dict(attrs).get('href')
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:self.cells.append(self.cell.strip());self.cell=None
        if tag=='tr' and self.href:self.rows.append((self.href,self.cells))


def nixos(source,cache,fetch):
    from .catalog import url_segura
    parser=ReleaseTable();parser.feed(fetch(source['url'],source['allowed_hosts'],cache).decode())
    rows=[]
    for href,cells in parser.rows:
        if len(cells)!=3 or not cells[1].isdigit() or not re.fullmatch('[a-f0-9]{64}',cells[2]):continue
        match=re.fullmatch(source['filename_pattern'],cells[0])
        if not match:continue
        # The official channel emits absolute release paths, relative to releases.nixos.org.
        url=urljoin('https://releases.nixos.org/',href);url_segura(url,source['allowed_hosts'])
        if urlsplit(url).hostname!='releases.nixos.org':raise ValueError('NixOS channel points outside its release host.')
        expected='/nixos/'+'.'.join(match['release'].split('.')[:2])+'/nixos-'+match['release']+'/'+cells[0]
        if urlsplit(url).path!=expected:raise ValueError('NixOS revision path does not match its filename.')
        rows.append({'original_url':url,'release':match['release'],'size_bytes':int(cells[1]),'sha256':cells[2],'checksum_source':source['url']})
    if not rows:raise ValueError('El canal NixOS no identifica la ISO mínima y su checksum.')
    return rows


def metalink(source,cache,fetch):
    """Use size/hash metadata served by the publisher, without probing a random mirror."""
    import xml.etree.ElementTree as ET
    from .catalog import url_segura
    from .catalog_downloads import lee_sumas,nombre_archivo
    url=source['artifact_url'];url_segura(url,source['allowed_hosts']);name=nombre_archivo(url)
    tree=ET.fromstring(fetch(source['url'],source['allowed_hosts'],cache))
    matches=[node for node in tree.iter() if node.tag.rsplit('}',1)[-1]=='file' and node.get('name')==name]
    if len(matches)!=1:raise ValueError('Metalink no identifica un único artefacto.')
    sizes=[int(node.text) for node in matches[0].iter() if node.tag.rsplit('}',1)[-1]=='size' and (node.text or '').isdigit()]
    hashes=[node.text.strip().lower() for node in matches[0].iter() if node.tag.rsplit('}',1)[-1]=='hash' and node.get('type','').lower() in ('sha-256','sha256') and node.text and re.fullmatch('[0-9a-fA-F]{64}',node.text.strip())]
    if len(set(sizes))!=1 or not sizes[0] or len(set(hashes))>1:raise ValueError('Metalink sin tamaño y SHA-256 inequívocos.')
    side=url+'.sha256';digest=lee_sumas(fetch(side,source['allowed_hosts'],cache).decode()).get(name)
    if not digest or (hashes and digest!=hashes[0]):raise ValueError('Metalink y checksum oficial no coinciden.')
    return [{'original_url':url,'sha256':digest,'size_bytes':sizes[0],'checksum_source':side,'release':source['release']}]
