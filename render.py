import os
import re
import argparse
import markdown
import shutil
from markdown.extensions import Extension
from markdown.extensions.meta import MetaExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from jinja2 import Environment, FileSystemLoader
from markdownTags import PreviewExtension, TagsExtension
from generateSitemap import generate_sitemap


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
        PreviewExtension(base_path=base_path, processor=convert_to_html), 
        TagsExtension(),
        MetaExtension(), 
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.toc',
        setup_codehilite(),
    ]
    md = markdown.Markdown(extensions=extensions)
    return md.convert(content)

def get_filename_without_extension(full_path):
    """Get the filename without extension from a full file path."""
    file_name_with_extension = os.path.basename(full_path)
    filename, _ = os.path.splitext(file_name_with_extension)
    return filename

def find_modules(directory):
    """Finds and returns a dictionary containing module filenames and their content."""
    module_dict = {}
    modules_dir = os.path.join(directory, 'modules')
    
    if not os.path.exists(modules_dir):
        return module_dict
    
    for root, _, files in os.walk(modules_dir):
        for file in files:
            file_path = os.path.join(root, file)
            module_dict[get_filename_without_extension(file)] = convert_to_html(read_file_content(file_path), os.path.dirname(file_path))   
    return module_dict

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
    # Find the first <p> block
    match = re.search(r'<h2>.*?</h2>.*?<p>(.*?)</p>', html, re.DOTALL)

    if not match:
        match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
    
    if match:
        paragraph_content = match.group(1)
        # Remove inner tags from the paragraph
        paragraph_text = re.sub(r'<.*?>', '', paragraph_content)
        paragraph_text = paragraph_text.strip()
        return paragraph_text[:155] + '...' if len(paragraph_text) > 160 else paragraph_text
    
    return ""  # No <p> block found

def get_image_meta_tags_html(markdown_text, current_dir, title, urlroot=''):
    pattern = r'!\[[^\]]*\]\((.*?)\)'
    match = re.search(pattern, markdown_text)

    if match and '! override_meta_img' in markdown_text:
        image_url = match.group(1)
        if image_url[:4] != 'http':
            image_url = os.path.join(urlroot, current_dir.replace('./', '')) + image_url 
    elif os.path.exists(os.path.join(current_dir, 'static/img/default_img.png')):
        image_url = urlroot + '/static/img/default_img.png'
    else:
        return ""

    meta_tags = f'''
    <meta property="og:image" content="{image_url}">
    <meta name="twitter:image" content="{image_url}">
    <meta name="twitter:title" content="{title}">
    '''

    return meta_tags

def get_first_title(markdown_or_html_text):
    pattern = r'(<h[1-6]>.*?</h[1-6]>)|^#+(\s+(.*?))$'
    match = re.search(pattern, markdown_or_html_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(0)).strip() # Strip HTML tags if present
        title = re.sub(r'#+ +', '', title)
        return title
    return None

def process_file(input_path, output_path, css, template_path, favicon, urlroot):
    """Processes the input directory and saves the files in the output directory."""
    # Copy the CSS file to the output directory
    copy_css_file(css, output_path)
    
    module_dict = find_modules(input_path)

    def match_to_module(match):
        return module_dict.get(match.group(1), None) if match else ""

    for root, dirs, files in os.walk(input_path):
        for dir_name in dirs:
            input_dir = os.path.join(root, dir_name)
            output_dir = input_dir.replace(input_path, output_path)
            os.makedirs(output_dir, exist_ok=True)

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = file_path.replace(input_path, '').lstrip('/\\')
            output_file = os.path.join(output_path, relative_path)

            title, meta_tags = None, None

            if 'modules' in file_path:
                # For files in 'modules', already handled in find_modules()
                continue

            if not file.lower().endswith(('.md', '.html')):
                # For non-md and non-html files, copy them as is to the output directory
                shutil.copy2(file_path, output_file)
                continue
            
            content = read_file_content(file_path)
            title = get_first_title(content)
            
            if file.lower().endswith('.md'):
                # If the file is markdown, convert to HTML and replace module tags
                meta_tags = get_image_meta_tags_html(content, root, title, urlroot)
                content = re.sub('! include (.+)', match_to_module, content, flags=re.I)
                content = re.sub('! .+', '', content) # clean out meta tags
                content = convert_to_html(content, os.path.dirname(file_path))


                # Change the file extension to '.html'
                output_file = os.path.splitext(output_file)[0].replace(', ', '-').replace(' ', '-') + '.html'

            # Fill in the template with the context information
            context = {
                'lang': 'en',  # Add the appropriate values for these context variables
                'meta_description': extract_first_paragraph(content),
                'root': urlroot,
                'favicon_path': get_dutluk_emoji_href(favicon),
                'title': title,
                'modules': module_dict,
                'content': content,
                'meta_tags': meta_tags
            }
            filled_template = fill_template({'context': context}, template_path)

            with open(output_file, 'w') as output_file:
                output_file.write(filled_template)

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description="Process files in input directory.")
    parser.add_argument('-i', '--input', help="Input directory path", required=True)
    parser.add_argument('-o', '--output', help="Output directory path", required=True)
    parser.add_argument('--css', help="CSS to include", required=False, default='themes/basic.css')
    parser.add_argument('--template', help="Path to the HTML template", required=False, default='templates/base.html')
    parser.add_argument('--favicon', help="Favicon emoji", required=False, default='👤')
    parser.add_argument('--root', help="Project url root", required=False, default='')
    args = parser.parse_args()

    process_file(args.input, args.output, args.css, args.template, args.favicon, args.root)
    generate_sitemap(args.output, args.root)
