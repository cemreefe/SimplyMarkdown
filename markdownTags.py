import os
import re
import xml.etree.ElementTree as ET
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.blockprocessors import BlockProcessor
from datetime import datetime

def get_first_title(markdown_or_html_text):
    pattern = r'(<h[1-6].*?>.+?</h[1-6]>)|#+(\s+(.*?))$'
    match = re.search(pattern, markdown_or_html_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(0)).strip() # Strip HTML tags if present
        title = re.sub(r'#+ +', '', title)
        return title
    return ""

class ContentItem:
    def __init__(self, content, date, href, emoji, tags, title, truncated):
        self.content = content
        self.date = date
        self.href = href
        self.emoji = emoji
        self.tags = tags
        self.title = title
        self.truncated = truncated

class PreviewExtension(Extension):
    """Markdown extension to handle the special tag for previews."""

    def __init__(self, base_path=None, processor=None, **kwargs):
        super().__init__(**kwargs)
        self.config = {
            'preview_limit': [6, "The number of components to show in the preview"]
        }
        self.base_path = base_path
        self.processor = processor

    def extendMarkdown(self, md):
        # Define the custom pattern for the special tag
        pattern = r'%\s*<([^>]+)>'
        preview_block = PreviewBlockProcessor(self.getConfigs(), md.parser, self.base_path, self.processor)
        preview_block.md = md
        md.parser.blockprocessors.register(preview_block, 'preview', 175)

class PreviewBlockProcessor(BlockProcessor):
    """Block processor for handling the special tag for previews."""

    def __init__(self, config, parser, base_path=None, processor=None):
        super().__init__(parser)
        self.directory_name = None
        self.preview_limit = int(config['preview_limit'])
        self.base_path = base_path
        self.processor = processor

    def test(self, parent, block):
        return re.match(r'^%\s*([^>]+)$', block)

    def run(self, parent, blocks):
        block = blocks.pop(0)  # Get the special tag line
        self.directory_name = re.match(r'^%\s*([^>]+)$', block).group(1).strip()
        content_context = self.get_preview_content()
        detailed = content_context.get('detailed', False)
        content_items = content_context.get('content_items', [])
        content_items = sorted(content_items, key=lambda x: x.date, reverse=True)

        wrapper = ET.Element('div', attrib={'class': 'postsListWrapper'})

        if detailed:
            for item in content_items:
                date_div = ET.Element('div', attrib={'class': 'previewDate'})
                date_div.text = item.date

                text_div = ET.Element('div')
                text_div.text = item.content

                a = ET.Element('a', attrib={'href': item.href, 'class': 'previewHref'})
                a.append(text_div)

                if item.truncated:
                    read_more = ET.Element('span', attrib={'class': 'a'})
                    read_more.text = '(Read more)'
                    a.append(read_more)

                post_wrapper = ET.Element('div', attrib={'class': 'postPreview'})
                post_wrapper.append(date_div)
                post_wrapper.append(a)

                wrapper.append(post_wrapper)

        else:
            prev_yr = None
            for item in content_items:
                yr = str(item.date.split('-')[0]) if item.date else None

                post_wrapper = ET.Element('div', attrib={'class': 'postTitle'})

                if yr != prev_yr:
                    date_div = ET.Element('div', attrib={'class': 'dateTab'})
                    date_div.text = yr
                    wrapper.append(date_div)
                    prev_yr = yr

                title_div = ET.Element('div')
                
                title_div.text = item.emoji + " " + item.title

                a = ET.Element('a', attrib={'href': item.href})
                a.append(title_div)

                post_wrapper.append(a)
                wrapper.append(post_wrapper)

        parent.append(wrapper)

    def get_preview_content(self):

        if not self.directory_name:
            return {}

        detailed = ':detailed' in self.directory_name
        self.directory_name = self.directory_name.replace(':detailed', '')

        directory_path = os.path.join(self.base_path, self.directory_name) if self.base_path else self.directory_name

        content_items = []

        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, _, files in sorted(os.walk(directory_path)):
                files.sort()
                relpath = os.path.relpath(root, directory_path)
                for file in files:
                    href = f"{self.directory_name}/{relpath}/{os.path.splitext(file)[0].replace(', ', '-').replace(' ', '-')}"
                    href += os.path.splitext(file)[1] if not os.path.splitext(file)[1] == '.md' else '.html'
                    href = href.replace(".html", "")

                    if file.lower().endswith('.md'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r') as md_file:
                            content = md_file.read().strip()
                            title = get_first_title(content)
                            content = content.replace('[TOC]', '')
                            components = content.split('\n\n')
                            components = [component for component in components if '<parsers-ignore>' not in component]
                            truncated = self.preview_limit < len(components)
                            components = components[:self.preview_limit]
                            content = '\n\n'.join(components) + '\n\n'
                            content = re.sub(r'\n@ [^\n]*', '', content, re.MULTILINE) # remove tags
                            content = re.sub(r'\n! [^\n]*', '', content, re.MULTILINE) # remove includes
                            content = re.sub(r'\n% [^\n]*', '', content, re.MULTILINE) # remove recursive path calls
                            content = re.sub(r'(\[.*?\]\()\.', r'\1 ' + self.directory_name + '/' + relpath + '/.', content)
                            content, meta = self.processor(content)
                            content = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', content)
                            content = re.sub(r'<h[2-4]\b[^>]*>(.*?)</h[2-4]>', r'<b>\1</b>', content)
                            content = re.sub(r'<h1\b[^>]*>(.*?)</h1>', r'<div class="preview-title"><h2>\1</h2></div>', content)

                            emoji = meta.get('emoji', [''])[0]
                            date = meta.get('date', [''])[0]
                            tags = meta.get('tags', [''])
                            content_items.append(ContentItem(content, date, href, emoji, tags, title, truncated))

        return {
            'content_items': list(reversed(content_items)),
            'detailed': detailed
        }

