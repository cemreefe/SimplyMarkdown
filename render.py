import sys
import os
import re
import markdown
import shutil
from jinja2 import Environment, FileSystemLoader
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree

# get directory path from command line argument
directory = sys.argv[1]
default_title = sys.argv[2] if len(sys.argv) > 2 else 'SimplyMarkdown'

# set up Jinja2 environment to load templates
env = Environment(loader=FileSystemLoader('templates'))

# create output directory if it doesn't exist
output_dir = os.path.join(directory, '../output')

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
                    href = './' + dirpath + '/' + os.path.splitext(relpath)[0] + '.html'
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


# read in the navbar file and convert it to HTML
with open(os.path.join(directory, 'navbar.md'), 'r') as f:
    navbar_markdown = f.read()
navbar_html = markdown.markdown(navbar_markdown, extensions=['markdown.extensions.extra', 'markdown.extensions.toc', SubdirLinkExtension(directory)])

def render_folder(directory, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # iterate through each file in the directory
    for filename in os.listdir(directory):
        # don't render navbar in a separate html file
        if filename == "navbar.md":
            pass
        # check if the file is a markdown file
        elif filename.endswith('.md'):
            # read in the markdown file contents
            with open(os.path.join(directory, filename), 'r') as f:
                markdown_content = f.read()

            title = re.search(r'#\s*(.*)', markdown_content)
            title = title.groups(0)[0] if title else default_title
            
            # convert the markdown to HTML using the Python-Markdown library
            html_content = markdown.markdown(markdown_content, extensions=['markdown.extensions.extra', 'markdown.extensions.toc', SubdirLinkExtension(directory)])
            
            # use Jinja2 to render the HTML content using a template
            template = env.get_template('base.html')
            rendered_html = template.render(content=html_content, navbar=navbar_html, title=title)
            
            # write out the rendered HTML to a new file in the output directory
            with open(os.path.join(output_dir, os.path.splitext(filename)[0] + '.html'), 'w') as f:
                f.write(rendered_html)
        # if another directory, recursively call render
        elif os.path.isdir(os.path.join(directory, filename)):
            render_folder(os.path.join(directory, filename), os.path.join(output_dir, filename))

def copy_static():
    static_dir = os.path.join(directory, 'static')
    output_static_dir = os.path.join(output_dir, 'static')
    if not os.path.exists(static_dir):
        return
    if not os.path.exists(output_static_dir):
        os.makedirs(output_static_dir)
    shutil.copytree(static_dir, output_static_dir, dirs_exist_ok = True)

render_folder(directory, output_dir)
copy_static()
