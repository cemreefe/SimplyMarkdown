import os
import argparse
import markdown
import shutil
from markdown.extensions import Extension
from markdown.extensions.meta import MetaExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from jinja2 import Environment, FileSystemLoader
from subdirectory_helpers import PreviewExtension


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

def process_file(input_path, output_path, css, template_path, favicon, root):
    """Processes the input directory and saves the files in the output directory."""
    # Copy the CSS file to the output directory
    copy_css_file(css, output_path)
    
    module_dict = find_modules(input_path)

    for root, dirs, files in os.walk(input_path):
        for dir_name in dirs:
            input_dir = os.path.join(root, dir_name)
            output_dir = input_dir.replace(input_path, output_path)
            os.makedirs(output_dir, exist_ok=True)

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = file_path.replace(input_path, '').lstrip('/\\')
            output_file = os.path.join(output_path, relative_path)

            if 'modules' in file_path:
                # For files in 'modules', already handled in find_modules()
                continue

            if not file.lower().endswith(('.md', '.html')):
                # For non-md and non-html files, copy them as is to the output directory
                shutil.copy2(file_path, output_file)
                continue

            if file.lower().endswith('.md'):
                # If the file is markdown, convert to HTML and replace module tags
                content = read_file_content(file_path)
                content = convert_to_html(content, os.path.dirname(file_path))

                # Change the file extension to '.html'
                output_file = os.path.splitext(output_file)[0] + '.html'

            # Fill in the template with the context information
            context = {
                'lang': 'en',  # Add the appropriate values for these context variables
                'meta_description': 'Website description',
                'root': root,
                'favicon_path': get_dutluk_emoji_href(favicon),
                'title': 'Page Title',
                'modules': module_dict,
                'content': content,
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