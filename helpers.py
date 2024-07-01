import os 
import re
import shutil 
from datetime import datetime
from markdownTags import PreviewExtension
from markdown.extensions.codehilite import CodeHiliteExtension
import markdown
from markdown.extensions import Extension
from jinja2 import Environment, FileSystemLoader

def setup_codehilite():
    # Define the options for the CodeHiliteExtension
    options = {
        'noclasses': True,
        'pygments_options': {'style': 'colorful'},
        'css_class': 'highlight',
        'use_pygments': True,
        'inline_css': True,
    }

    # Create an instance of the CodeHiliteExtension with the modified options
    return CodeHiliteExtension(**options)

def read_file_content(file_path):
    """Reads and returns the content of a file."""
    with open(file_path, 'r') as file:
        return file.read()

def convert_to_html(content, base_path=''):
    """Converts markdown content to HTML."""
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.toc',
        'meta',
        PreviewExtension(base_path=base_path, processor=convert_to_html), 
        setup_codehilite(),
    ]
    md = markdown.Markdown(extensions=extensions)
    return md.convert(content), md.Meta

def get_filename_without_extension(full_path):
    """Get the filename without extension from a full file path."""
    file_name_with_extension = os.path.basename(full_path)
    filename, _ = os.path.splitext(file_name_with_extension)
    return filename

def fill_template(context, template_path):
    """Fills the HTML template with the given context."""
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))
    return template.render(context)

def copy_css_file(css_path, output_path):
    """Copy the CSS file to the output directory."""
    css_file_name = "theme.css"
    css_output_dir = os.path.join(output_path, 'static', 'css')
    os.makedirs(css_output_dir, exist_ok=True)  # Create the directory if it doesn't exist
    output_css_path = os.path.join(css_output_dir, css_file_name)
    shutil.copy2(css_path, output_css_path)

def get_dutluk_emoji_href(emoji):
    return f"https://emoji.dutl.uk/png/64x64/{emoji}.png"

def extract_first_paragraph(html):
    # Find all <p> tags and their inner text
    p_tags = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)

    # Iterate through the extracted <p> tags and find the first significant one
    for p_content in p_tags:
        # Remove inner tags from the paragraph
        paragraph_text = re.sub(r'<parsers-ignore>.*?</parsers-ignore>', '', p_content)
        paragraph_text = re.sub(r'<.*?>', '', paragraph_text)
        paragraph_text = paragraph_text.strip()

        # Check if the paragraph is significant (contains at least 30 characters)
        if len(paragraph_text) >= 30:
            return paragraph_text[:155] + '...' if len(paragraph_text) > 160 else paragraph_text

    return ""  # No significant <p> block found


def get_meta_tags(meta_img_override, meta_title, meta_description, meta_pubdate='', urlroot='', current_dir='', input_path='', output_file_relpath='', meta_canonical_uri_override=None):
    current_dir_relpath = os.path.relpath(current_dir, input_path)

    canonical_url = os.path.join(urlroot, meta_canonical_uri_override or output_file_relpath)
    canonical_url = canonical_url.replace(".html", "")

    if meta_img_override:
        meta_img = meta_img_override
        if meta_img[:4] != 'http':
            meta_img = os.path.join(urlroot, current_dir_relpath, meta_img)
    else:
        meta_img = urlroot + '/static/img/default_img.png'

    # Determine the last modification date of the file
    file_path = os.path.join(current_dir, output_file_relpath)
    pub_date = datetime.strptime(meta_pubdate, "%Y-%m-%d").strftime('%a, %d %b %Y %H:%M:%S +0000') if meta_pubdate else None

    meta_tags = f'''
    <meta property="og:title" name="title" content="{meta_title}" />
    <meta property="og:image" name="image" content="{meta_img}" />
    <meta property="og:description" name="description" content="{meta_description}" />
    <meta property="og:type" content="website" />
    <meta property="og:url" name="url" content="{canonical_url}">
    <meta property="twitter:title" name="title" content="{meta_title}" />
    <meta property="twitter:image" name="image" content="{meta_img}" />
    <link rel="canonical" href="{canonical_url}" />
    '''

    if pub_date:
        meta_tags += f'<meta property="og:pubdate" name="pubdate" content="{pub_date}" />\n'

    return meta_tags
