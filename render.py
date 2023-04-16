import sys
import os
import re
import markdown
import shutil
from jinja2 import Environment, FileSystemLoader
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree
import argparse

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
theme = args.theme if args.theme else 'templates/basic.css'
root = args.root if args.root else ''

# set up Jinja2 environment to load templates
env = Environment(loader=FileSystemLoader('templates'))

# define a custom markdown extension that adds links to all files in subdirectories
class SubdirLinkExtension(Extension):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
    def extendMarkdown(self, md):
        subdir_link_pattern = SubdirLinkPattern(r'%\s*([^\s]+)', md, self.base_dir)
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
                    href = './' + dirpath + '/' + os.path.splitext(relpath)[0].replace(' ', '-') + '.html'
                    link = etree.Element('a')
                    link.set('href', href)
                    link.text = os.path.splitext(f)[0]
                    links.append(link)
                    # create a new ul element
            ul = etree.Element('ul')
            # append a new li element for each link
            for link in links:
                li = etree.Element('li')
                li.append(link)
                ul.append(li)
            return ul
        else:
            return None


def markdown_to_html(directory, filename):
    if os.path.join(directory, filename):
        with open(os.path.join(directory, filename), 'r') as f:
            markdown_str = f.read()
        return markdown.markdown(markdown_str, extensions=['markdown.extensions.extra', 'markdown.extensions.toc', SubdirLinkExtension(directory)])
    else: 
        return ""

# Convert navbar.md to HTML
navbar_html = markdown_to_html(directory, 'navbar.md')

# Convert footer.md to HTML
footer_html = markdown_to_html(directory, 'footer.md')

def render_folder(directory, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(directory):
        if filename in ("navbar.md", "footer.md"):
            continue
        if os.path.basename(filename)[0] == "_":
            continue
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and filepath.endswith('.md'):
            with open(filepath, 'r') as f:
                markdown_content = f.read()
            title = default_title
            match = re.search(r'#\s*(.*)', markdown_content)
            if match:
                title += f" | {match.group(1)}"
            html_content = markdown.markdown(
                markdown_content,
                extensions=['markdown.extensions.extra', 'markdown.extensions.toc', SubdirLinkExtension(directory)]
            )
            template = env.get_template('base.html')
            rendered_html = template.render(
                content=html_content, 
                navbar=navbar_html, 
                footer=footer_html, 
                title=title, 
                root=root
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
