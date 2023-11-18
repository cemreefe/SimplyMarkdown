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
            'preview_limit': [4, "The number of components to show in the preview"]
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
        content_context = self.get_preview_content()
        contents = content_context.get('contents', [])
        dates = content_context.get('dates', [])
        hrefs = content_context.get('hrefs', [])
        emojis = content_context.get('emojis', [])
        detailed = content_context.get('detailed', False)

        wrapper = ET.Element('div', attrib={'class': 'postsListWrapper'})

        if detailed:
            for content, date, href, emoji in zip(contents, dates, hrefs, emojis):

                # Create the child <div> element for the date with the class 'previewDate'
                date_div = ET.Element('div', attrib={'class': 'previewDate'})
                date_div.text = date

                text_div = ET.Element('div')
                text_div.text = emoji + content + '(Read more)'

                # Create the anchor (<a>) element with the provided href
                a = ET.Element('a', attrib={'href': href, 'class':'previewHref'})
                a.append(text_div)

                post_wrapper = ET.Element('div', attrib={'class': 'postPreview'})
                post_wrapper.append(date_div)
                post_wrapper.append(a)

                wrapper.append(post_wrapper)
        
        else:
            prev_yr = None
            for content, date, href, emoji in zip(contents, dates, hrefs, emojis):
                yr = date.split('/')[0]

                post_wrapper = ET.Element('div', attrib={'class': 'postTitle'})

                if yr != prev_yr:

                    # Create the child <div> element for the date with the class 'previewDate'
                    date_div = ET.Element('div', attrib={'class': 'dateTab'})
                    date_div.text = yr
                    wrapper.append(date_div)
                    prev_yr = yr

                from render import get_first_title

                title_div = ET.Element('div')
                title_div.text = emoji + get_first_title(content)

                # Create the anchor (<a>) element with the provided href
                a = ET.Element('a', attrib={'href': href})
                a.append(title_div)

                post_wrapper.append(a)

                wrapper.append(post_wrapper)

        parent.append(wrapper)
                
    def get_preview_content(self):
        if not self.directory_name:
            return {}


        detailed = False

        if ':detailed' in self.directory_name:
            self.directory_name = self.directory_name.replace(':detailed', '')
            detailed = True

        if self.base_path:
            directory_path = os.path.join(self.base_path, self.directory_name)
        else:
            directory_path = self.directory_name

        contents, dates, hrefs, emojis = [], [], [], []

        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, _, files in sorted(os.walk(directory_path)):
                files.sort()
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
                            content = re.sub(r'(\[.*?\]\()\.', r'\1 ' + self.directory_name + '/' + relpath + '/.', content)
                            emoji_match = re.search(r'! emoji (.+)', content)
                            emojis.append(emoji_match.group(1) + ' ' if emoji_match else '')
                            content = re.sub(r'\n! emoji [^\n]*', '', content, re.MULTILINE) # remove emoji descriptor
                            content = re.sub(r'\n@ [^\n]*', '', content, re.MULTILINE) # remove tags
                            
                            content = self.processor(content)
                            content = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', content) # remove links
                            content = re.sub(r'<h[2-4]\b[^>]*>(.*?)</h[2-4]>', r'<b>\1</b>', content) # remove make headers below h1 b
                            content = re.sub(r'<h1\b[^>]*>(.*?)</h1>', r'<b class="preview-title">\1</b>', content) # make h1 headers into large b
                            contents.append(content)
                            dates.append(date)
                            hrefs.append(href)

        return {
            'contents': reversed(contents), 
            'dates': reversed(dates), 
            'hrefs': reversed(hrefs), 
            'detailed': detailed,
            'emojis': reversed(emojis)
        }


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
