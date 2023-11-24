import os
import re
import xml.etree.ElementTree as ET
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.blockprocessors import BlockProcessor

import frontmatter 

class ContentItem:
    def __init__(self, content, date, href, emoji, tags):
        self.content = content
        self.date = date
        self.href = href
        self.emoji = emoji
        self.tags = tags

class PreviewExtension(Extension):
    """Markdown extension to handle the special tag for previews."""

    def __init__(self, base_path=None, processor=None, **kwargs):
        super().__init__(**kwargs)
        self.config = {
            'preview_limit': [4, "The number of components to show in the preview"]
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

        wrapper = ET.Element('div', attrib={'class': 'postsListWrapper'})

        if detailed:
            for item in content_items:
                date_div = ET.Element('div', attrib={'class': 'previewDate'})
                date_div.text = item.date

                text_div = ET.Element('div')
                text_div.text = item.content + '(Read more)'

                a = ET.Element('a', attrib={'href': item.href, 'class': 'previewHref'})
                a.append(text_div)

                post_wrapper = ET.Element('div', attrib={'class': 'postPreview'})
                post_wrapper.append(date_div)
                post_wrapper.append(a)

                wrapper.append(post_wrapper)

        else:
            prev_yr = None
            for item in content_items:
                yr = item.date.split('/')[0]

                post_wrapper = ET.Element('div', attrib={'class': 'postTitle'})

                if yr != prev_yr:
                    date_div = ET.Element('div', attrib={'class': 'dateTab'})
                    date_div.text = yr
                    wrapper.append(date_div)
                    prev_yr = yr

                from render import get_first_title

                title_div = ET.Element('div')
                title_div.text = item.emoji + get_first_title(item.content)

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
                    date = relpath
                    href = f"{self.directory_name}/{relpath}/{os.path.splitext(file)[0].replace(', ', '-').replace(' ', '-')}"
                    href += os.path.splitext(file)[1] if not os.path.splitext(file)[1] == '.md' else '.html'

                    if file.lower().endswith('.md'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r') as md_file:
                            post = frontmatter.load(md_file)
                            content = post.content.strip()
                            components = content.split('\n\n')[:self.preview_limit]
                            content = '\n\n'.join(components) + '\n\n'
                            content = self.processor(content)
                            content = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', content)
                            content = re.sub(r'<h[2-4]\b[^>]*>(.*?)</h[2-4]>', r'<b>\1</b>', content)
                            content = re.sub(r'<h1\b[^>]*>(.*?)</h1>', r'<div class="preview-title"><b>\1</b></div>', content)

                            emoji = post.metadata.get('emoji', '')
                            tags = post.metadata.get('tags', '')
                            content_items.append(ContentItem(content, date, href, emoji, tags=[]))

        return {
            'content_items': list(reversed(content_items)),
            'detailed': detailed
        }

# Define a custom markdown extension that adds tags
class TagsExtension(Extension):
    def extendMarkdown(self, md):
        tags_pattern = TagsPattern(r'^@\s+(.+)', md)
        md.inlinePatterns.register(tags_pattern, 'tags', 180)

class TagsPattern(Pattern):
    def handleMatch(self, m):
        tags = m.group(2)
        tags = [tag.strip() for tag in tags.split(',')]
        tags_container = ET.Element('div')
        for tag in tags:
            tag_block = ET.Element('div', {'class': 'categoryTag'})
            tag_block.text = tag
            tags_container.append(tag_block)
        return tags_container
