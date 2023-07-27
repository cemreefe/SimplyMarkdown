import os
import re
import markdown
import xml.etree.ElementTree as ET
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern

class PreviewExtension(markdown.extensions.Extension):
    """Markdown extension to handle the special tag for previews."""

    def __init__(self, base_path=None, processor=None, **kwargs):
        self.config = {
            'preview_limit': [5, "The number of components to show in the preview"]
        }
        self.base_path = base_path
        self.processor = processor
        super(PreviewExtension, self).__init__(**kwargs)

    def extendMarkdown(self, md):
        # Define the custom pattern for the special tag
        pattern = r'%\s*<([^>]+)>'
        preview_block = PreviewBlockProcessor(self.getConfigs(), md.parser, self.base_path, self.processor)
        preview_block.md = md
        md.parser.blockprocessors.register(preview_block, 'preview', 175)

class PreviewBlockProcessor(markdown.blockprocessors.BlockProcessor):
    """Block processor for handling the special tag for previews."""

    def __init__(self, config, parser, base_path=None, processor=None):
        self.directory_name = None
        self.preview_limit = int(config['preview_limit'])
        self.base_path = base_path
        self.processor = processor
        super(PreviewBlockProcessor, self).__init__(parser)

    def test(self, parent, block):
        return re.match(r'^%\s*([^>]+)$', block)

    def run(self, parent, blocks):
        block = blocks.pop(0)  # Get the special tag line
        self.directory_name = re.match(r'^%\s*([^>]+)$', block).group(1).strip()
        contents, dates, hrefs = self.get_preview_content()

        for content, date, href in zip(contents, dates, hrefs):

            # Create the child <div> element for the date with the class 'previewDate'
            date_div = ET.Element('div', attrib={'class': 'previewDate'})
            date_div.text = date

            text_div = ET.Element('div')
            text_div.text = content

            more_div = ET.Element('div', attrib={'style': 'text-align: right'})
            more_div.text = 'Read more'

            wrapper = ET.Element('div', attrib={'class': 'postPreview'})
            wrapper.append(date_div)
            wrapper.append(text_div)
            wrapper.append(more_div)

            # Create the anchor (<a>) element with the provided href
            a = ET.Element('a', attrib={'href': href, 'class':'previewHref'})
            a.append(wrapper)

            parent.append(a)

    def get_preview_content(self):
        if not self.directory_name:
            return ''

        if self.base_path:
            directory_path = os.path.join(self.base_path, self.directory_name)
        else:
            directory_path = self.directory_name

        contents, dates, hrefs = [], [], []

        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, _, files in os.walk(directory_path):
                relpath = os.path.relpath(root, directory_path)
                for file in files:
                    date = relpath
                    href =  (self.directory_name + '/' + relpath + '/' + os.path.splitext(file)[0].replace(', ', '-').replace(' ', '-')) 
                    href = href +  (os.path.splitext(file)[1] if not os.path.splitext(file)[1] == '.md' else '.html')
                    if file.lower().endswith('.md'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r') as md_file:
                            file_content = md_file.read().strip()
                            components = file_content.split('\n\n')[:self.preview_limit]
                            content = '\n\n'.join(components) + '\n\n'
                            content = self.processor(content)
                            contents.append(content)
                            dates.append(date)
                            hrefs.append(href)

        return contents, dates, hrefs


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
