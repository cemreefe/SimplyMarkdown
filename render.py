import argparse
import markdown
import re
import shutil
import sys
import os

from jinja2 import Environment, FileSystemLoader
from markdown.extensions import Extension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.inlinepatterns import Pattern
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Argument parser example')
parser.add_argument('-i', '--input_dir', type=str, help='Input directory')
parser.add_argument('-o', '--output_dir', type=str, help='Output directory')
parser.add_argument('-t', '--title', type=str, help='Title')
parser.add_argument('-th', '--theme', type=str, help='CSS Theme file location')
parser.add_argument('--root', type=str, help='Path to website root if different from url root')
parser.add_argument('--favicon', type=str, help='Emoji favicon')
parser.add_argument('--lang', type=str, help='Website language')

args = parser.parse_args()

directory = args.input_dir
output_dir = args.output_dir if args.output_dir else os.path.join(directory, '../output')
default_title = args.title if args.title else '<<Title>>'
theme = args.theme if args.theme else 'themes/basic.css'
urlroot = args.root if args.root else ''
favicon_path = f'https://emoji.dutl.uk/png/32x32/{args.favicon}.png' if args.favicon else f'{urlroot}/static/favicon/favicon.png'
lang = args.root if args.root else 'en'

# set up Jinja2 environment to load templates
env = Environment(loader=FileSystemLoader('templates'))

# Define the options for the CodeHiliteExtension
options = {
    'noclasses': True,
    'pygments_options': {'style': 'colorful'},
    'css_class': 'highlight',
    'use_pygments': True,
    'inline_css': True,
}

# Create an instance of the CodeHiliteExtension with the modified options
codehilite = CodeHiliteExtension(**options)

# define a custom markdown extension that adds links to all files in subdirectories
class SubdirLinkExtension(Extension):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
    def extendMarkdown(self, md):
        subdir_link_pattern = SubdirLinkPattern(r'^%\s+([^\s]+)', md, self.base_dir)
        md.inlinePatterns.register(subdir_link_pattern, 'subdir_link', 175)

class SubdirLinkPattern(Pattern):
    def __init__(self, pattern, md, base_dir):
        super(SubdirLinkPattern, self).__init__(pattern)
        self.md = md
        self.base_dir = base_dir

    def handleMatch(self, m):
        dirpath = m.group(2)
        full_path = os.path.join(self.base_dir, dirpath)
        if os.path.isdir(full_path):
            items = []
            for root, dirs, files in os.walk(full_path):
                for f in files:
                    path = os.path.join(root, f)
                    relpath = os.path.relpath(path, full_path)
                    # TODO: handle non-html files
                    href = './' + dirpath + '/' + os.path.splitext(relpath)[0].replace(' ', '-')
                    link = ET.Element('a', href=href)
                    date = ET.Element('span')
                    date.text = '/'.join(relpath.split('/')[:-1]) + " "
                    link.text = os.path.splitext(f)[0]
                    items.append((date, link))

            # create a new ul element
            ul_elem = ET.Element('ul')
            for date, link in items:
                li_elem = ET.Element('li')
                li_elem.append(date)
                li_elem.append(link)
                ul_elem.append(li_elem)
            return ul_elem
        else:
            return None

# define a custom markdown extension that adds tags
class TagsExtension(Extension):
    def __init__(self):
        super().__init__()
        
    def extendMarkdown(self, md):
        tags_pattern = TagsPattern(r'^@\s+(.+)', md)
        md.inlinePatterns.register(tags_pattern, 'tags', 180)

class TagsPattern(Pattern):
    def __init__(self, pattern, md):
        super(TagsPattern, self).__init__(pattern)
        self.md = md

    def handleMatch(self, m):
        tags = m.group(2)
        tags = [tag.strip() for tag in tags.split(',')]
        tags_container = ET.Element('div')
        for tag in tags:
            tag_block = ET.Element('div', {'class': 'categoryTag'}) # Add class attribute
            tag_block.text = tag # Set tag as text content of div element
            tags_container.append(tag_block)
        return tags_container




def markdown_to_html(directory, markdown_str):
    return markdown.markdown(
        markdown_str, 
        extensions=[
            'markdown.extensions.extra', 
            'markdown.extensions.fenced_code',
            'markdown.extensions.toc', 
            SubdirLinkExtension(directory),
            TagsExtension(),
            codehilite
        ]
    )

def read_html(directory, filename):
    if os.path.exists(os.path.join(directory, filename)):
        with open(os.path.join(directory, filename), 'r') as f:
            return f.read()
    else: 
        return ""

def markdown_file_to_html(directory, filename):
    if os.path.exists(os.path.join(directory, filename)):
        with open(os.path.join(directory, filename), 'r') as f:
            markdown_str = f.read()
        return markdown_to_html(directory, markdown_str)
    else: 
        return ""


def get_image_meta_tags_html(markdown_text):
    pattern = r'!\[[^\]]*\]\((.*?)\)'
    match = re.search(pattern, markdown_text)
    if match and ('!override_meta_img' in markdown_text):
        image_url = match.group(1)
        return f'<meta property="og:image" content="{image_url}">\n\t\t<meta name="twitter:image" content="{image_url}">'
    elif os.path.exists(os.path.join(directory, 'static/img/default_img.png')):
        image_url = urlroot + '/static/img/default_img.png'
        return f'<meta property="og:image" content="{image_url}">\n\t\t<meta name="twitter:image" content="{image_url}">'
    else:
        return ""

def extract_first_paragraph(html):
    # Find the first <p> block
    match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
    
    if match:
        paragraph_content = match.group(1)
        
        # Remove inner tags from the paragraph
        paragraph_text = re.sub(r'<.*?>', '', paragraph_content)
        
        return paragraph_text.strip()
    
    return ""  # No <p> block found

def extension(filename):
    assert (len(filename.split('.')) == 2)
    return filename.split('.')[-1]

def barename(filename):
    assert (len(filename.split('.')) == 2)
    return filename.split('.')[0]

def get_modules():
    modules_ = {}
    modules_dir = os.path.join(directory, '_modules')
    for filename in os.listdir(modules_dir):
        filepath = os.path.join(modules_dir, filename)
        if extension(filename) == 'md':
            modules_[barename(filename)] = markdown_file_to_html('', filepath)
        if extension(filename) == 'html':
            modules_[barename(filename)] = read_html('', filepath)
    return modules_

modules = get_modules()

def render_folder(directory, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(directory):
        # pre-rendered special files
        if filename in ("navbar.md", "footer.md", "socials_tag.md", "head_extras.html"):
            continue
        # ignore files that start with _
        if os.path.basename(filename)[0] == "_":
            continue
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and filepath.endswith('.md'):
            with open(filepath, 'r') as f:
                markdown_content = f.read()
            title = default_title
            # set page title to include the first h1 if exists
            match = re.search(r'#\s*(.*)', markdown_content)
            if match:
                title = f"{match.group(1)} | {title}"
            # if [SOCIALS] tag, replace with rendered socials module
            markdown_content = markdown_content.replace("[SOCIALS]", modules.get('socials', ''))
            meta_tags_html = get_image_meta_tags_html(markdown_content)
            markdown_content = markdown_content.replace("!override_meta_img", "")
            content_html = markdown_to_html(directory, markdown_content)
            template = env.get_template('base.html')
            rendered_html = template.render(
                context = {
                    'content': content_html, 
                    'navbar': modules.get('navbar', ''), 
                    'footer': modules.get('footer', ''), 
                    'title': title, 
                    'root': urlroot,
                    'head_extras': modules.get('head_extras', '') + meta_tags_html,
                    'favicon_path': favicon_path,
                    'lang': lang,
                    'meta_description': extract_first_paragraph(content_html)
                }
            )
            with open(os.path.join(output_dir, os.path.splitext(filename)[0].replace(' ', '-') + '.html'), 'w') as f:
                f.write(rendered_html)
        elif os.path.isdir(filepath):
            render_folder(filepath, os.path.join(output_dir, filename))
        else:
            shutil.copy(filepath, os.path.join(output_dir, filename))


def copy_static():
    static_dir = os.path.join(directory, 'static')
    output_static_dir = os.path.join(output_dir, 'static')
    os.makedirs(output_static_dir, exist_ok=True)
    if os.path.exists(static_dir):
        shutil.copytree(static_dir, output_static_dir, dirs_exist_ok=True)
    if theme != 'none':
        os.makedirs(os.path.join(output_static_dir, 'css'), exist_ok=True)
        theme_css = os.path.join(output_static_dir, 'css', 'theme.css')
        shutil.copy(theme, theme_css)


render_folder(directory, output_dir)
copy_static()
