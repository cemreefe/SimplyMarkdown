import os
import re
import markdown
import xml.etree.ElementTree as ET

class PreviewExtension(markdown.extensions.Extension):
    """Markdown extension to handle the special tag for previews."""

    def __init__(self, base_path=None, processor=None, **kwargs):
        self.config = {
            'preview_limit': [10, "The number of components to show in the preview"]
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
        content = self.get_preview_content()
        div = ET.Element('div', attrib={'class': 'postPreview'})
        div.text = content
        parent.append(div)

    def get_preview_content(self):
        if not self.directory_name:
            return ''

        content = ""
        if self.base_path:
            directory_path = os.path.join(self.base_path, self.directory_name)
        else:
            directory_path = self.directory_name

        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith('.md'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r') as md_file:
                            file_content = md_file.read().strip()
                            components = file_content.split('\n\n')[:self.preview_limit]
                            content += '\n\n'.join(components) + '\n\n'
                            content = self.processor(content)

        return content


