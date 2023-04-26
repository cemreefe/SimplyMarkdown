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

args = parser.parse_args()

directory = args.input_dir
output_dir = args.output_dir if args.output_dir else os.path.join(directory, '../output')
default_title = args.title if args.title else '<<Title>>'
theme = args.theme if args.theme else 'themes/basic.css'
root = args.root if args.root else ''

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
            links = []
            for root, dirs, files in os.walk(full_path):
                for f in files:
                    path = os.path.join(root, f)
                    relpath = os.path.relpath(path, full_path)
                    # TODO: handle non-html files
                    href = './' + dirpath + '/' + os.path.splitext(relpath)[0].replace(' ', '-')
                    link = ET.Element('a', href=href)
                    link.text = os.path.splitext(f)[0]
                    links.append(link)

            # create a new ul element
            ul_elem = ET.Element('ul')
            for link in links:
                li_elem = ET.Element('li')
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
    if match:
        image_url = match.group(1)
        return f'<meta property="og:image" content="{image_url}">\n\t\t<meta name="twitter:image" content="{image_url}">'
    else:
        return ""


# Convert navbar.md to HTML
navbar_html = markdown_file_to_html(directory, 'navbar.md')

# Convert socials.md to HTML
socials_html = markdown_file_to_html(directory, 'socials_tag.md')

# Convert footer.md to HTML
footer_html = markdown_file_to_html(directory, 'footer.md')

# Convert head_extras.md to HTML
head_extras_html = markdown_file_to_html(directory, 'head_extras.md')

def render_folder(directory, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(directory):
        # pre-rendered special files
        if filename in ("navbar.md", "footer.md", "socials_tag.md"):
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
            markdown_content = markdown_content.replace("[SOCIALS]", socials_html)
            content_html = markdown_to_html(directory, markdown_content)
            template = env.get_template('base.html')
            rendered_html = template.render(
                context = {
                    'content':content_html, 
                    'navbar':navbar_html, 
                    'footer':footer_html, 
                    'title':title, 
                    'root':root,
                    'head_extras':head_extras_html + get_image_meta_tags_html(markdown_content)  
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
