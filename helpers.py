import os 
import re
import shutil 
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
        paragraph_text = re.sub(r'<.*?>', '', p_content)
        paragraph_text = paragraph_text.strip()

        # Check if the paragraph is significant (contains at least 30 characters)
        if len(paragraph_text) >= 30:
            return paragraph_text[:155] + '...' if len(paragraph_text) > 160 else paragraph_text

    return ""  # No significant <p> block found


def get_meta_tags(meta_img_override, meta_title, meta_description, urlroot='', current_dir='', input_path=''):
    
    current_dir_relpath = os.path.relpath(current_dir, input_path)

    if meta_img_override:
        meta_img = meta_img_override
        if meta_img[:4] != 'http':
            meta_img = os.path.join(urlroot, current_dir_relpath, meta_img) 
    else:
        meta_img = urlroot + '/static/img/default_img.png'

    meta_tags = f'''
    <meta property="og:image" content="{meta_img}">
    <meta name="twitter:image" content="{meta_img}">
    <meta name="twitter:title" content="{meta_title}">
    <meta name="description" content="{{ meta_description }}">
    '''

    return meta_tags
