import os
import fnmatch
import argparse
from xml.etree.ElementTree import Element, SubElement, ElementTree
from bs4 import BeautifulSoup

def extract_metadata(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('title').text if soup.find('title') else 'No title'
    pub_date_meta = soup.find('meta', {'name': 'pubDate'}) or soup.find('meta', {'name': 'pubdate'})
    pub_date = pub_date_meta['content'] if pub_date_meta else None
    main_content = str(soup.find('main')) if soup.find('main') else 'No content'

    return title, pub_date, main_content

def parse_main_content(main_content):
    soup = BeautifulSoup(main_content, 'html.parser')

    # Remove all <script> and <style> elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()

    # Remove all style attributes
    for tag in soup.find_all(True):
        tag.attrs = {key: value for key, value in tag.attrs.items() if key != 'style'}

    cleaned_content = str(soup)
    return cleaned_content

def generate_rss_feed(root_directory, urlroot='', uri_whitelist='*', feed_title='My RSS Feed', feed_description='This is an RSS feed of my website.'):
    def get_html_files(directory):
        html_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.html'):
                    file_path = os.path.join(root, file)
                    html_files.append(file_path)
        return html_files

    def is_uri_whitelisted(uri, whitelist_patterns):
        for pattern in whitelist_patterns:
            print(">>", pattern, whitelist_patterns)
            if fnmatch.fnmatch(uri, pattern):
                return True
        return False

    html_files = get_html_files(root_directory)
    whitelist_patterns = uri_whitelist.split(',')

    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    title = SubElement(channel, 'title')
    title.text = feed_title
    link = SubElement(channel, 'link')
    link.text = urlroot
    description = SubElement(channel, 'description')
    description.text = feed_description

    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        item_title, pub_date, main_content = extract_metadata(html_content)
        url = file_path.replace(root_directory, urlroot + '/').replace('\\', '/').lstrip('/')
        url = url.replace('//', '/')
        url = url.replace('https:/', 'https://')
        url = url.replace(".html", "")

        uri = file_path.replace(root_directory, '')
        if not is_uri_whitelisted(uri, whitelist_patterns):
            continue

        parsed_content = parse_main_content(main_content)

        item = SubElement(channel, 'item')
        item_title_elem = SubElement(item, 'title')
        item_title_elem.text = item_title
        link_elem = SubElement(item, 'link')
        link_elem.text = url
        guid_elem = SubElement(item, 'guid')
        guid_elem.text = url
        if pub_date:
            pub_date_elem = SubElement(item, 'pubDate')
            pub_date_elem.text = pub_date
        description_elem = SubElement(item, 'description')
        description_elem.text = parsed_content

    output_file = os.path.join(root_directory, 'rss.xml')
    ElementTree(rss).write(output_file, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate an RSS feed from HTML files.')
    parser.add_argument('root_directory', help='Root directory containing HTML files.')
    parser.add_argument('--urlroot', default='', help='Root URL for the RSS feed links.')
    parser.add_argument('--whitelist', default='*', help='Comma-separated list of URI patterns to include in the feed (supports wildcards).')
    parser.add_argument('--title', default='My RSS Feed', help='Title of the RSS feed.')
    parser.add_argument('--description', default='This is an RSS feed of my website.', help='Description of the RSS feed.')

    args = parser.parse_args()
    generate_rss_feed(args.root_directory, args.urlroot, args.whitelist, args.title, args.description)
