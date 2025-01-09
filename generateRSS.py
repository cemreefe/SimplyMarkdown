import os
import fnmatch
import argparse
from xml.etree.ElementTree import Element, SubElement, ElementTree
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime

def extract_metadata(html_content, last_edit):
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('title').text if soup.find('title') else 'No title'
    pub_date_meta = soup.find('meta', {'name': 'pubDate'}) or soup.find('meta', {'name': 'pubdate'})
    pub_date = pub_date_meta['content'] if pub_date_meta else None
    pub_date = pub_date or last_edit
    main_content = str(soup.find('main')) if soup.find('main') else 'No content'

    return title, pub_date, main_content

def parse_main_content(main_content):
    soup = BeautifulSoup(main_content, 'html.parser')

    # Remove all <script> and <style> elements
    for script_or_style in soup(['script', 'style', 'parsers-ignore']):
        script_or_style.decompose()

    # Remove all style attributes
    for tag in soup.find_all(True):
        tag.attrs = {key: value for key, value in tag.attrs.items() if key != 'style'}

    # Add max-width:100% to all img elements
    for img in soup.find_all('img'):
        img['style'] = 'max-width:100%;'

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

    feed_items = []

    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        last_edit = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%a, %d %b %Y %H:%M:%S +0000") # Naive, assume UTC
        item_title, pub_date, main_content = extract_metadata(html_content, last_edit)
        url = file_path.replace(root_directory, urlroot + '/').replace('\\', '/').lstrip('/')
        url = url.replace('//', '/')
        url = url.replace('https:/', 'https://')
        url = url.replace(".html", "")

        uri = file_path.replace(root_directory, '')
        if not is_uri_whitelisted(uri, whitelist_patterns):
            continue

        parsed_content = parse_main_content(main_content)

        feed_items.append({
            'title': item_title,
            'link': url,
            'guid': url,
            'pubDate': pub_date,
            'description': parsed_content
        })

    # Sort items by pubDate in descending order
    def sort_key(item):
        if item['pubDate']:
            try:
                return parsedate_to_datetime(item['pubDate'])
            except (TypeError, ValueError):
                pass
        return datetime.min  # Default to the oldest possible date for items without valid pubDate

    feed_items.sort(key=sort_key, reverse=True)

    for item_data in feed_items:
        item = SubElement(channel, 'item')
        item_title_elem = SubElement(item, 'title')
        item_title_elem.text = item_data['title']
        link_elem = SubElement(item, 'link')
        link_elem.text = item_data['link']
        guid_elem = SubElement(item, 'guid')
        guid_elem.text = item_data['guid']
        if item_data['pubDate']:
            pub_date_elem = SubElement(item, 'pubDate')
            pub_date_elem.text = item_data['pubDate']
        description_elem = SubElement(item, 'description')
        description_elem.text = item_data['description']

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
