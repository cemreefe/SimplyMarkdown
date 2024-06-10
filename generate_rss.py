import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from bs4 import BeautifulSoup

def extract_metadata(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('title').text if soup.find('title') else 'No title'
    pub_date = soup.find('meta', {'name': 'pubDate'}) or soup.find('meta', {'name': 'pubdate'})
    return title, pub_date

def generate_rss_feed(root_directory, urlroot=''):
    def get_html_files(directory):
        html_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.html'):
                    file_path = os.path.join(root, file)
                    html_files.append(file_path)
        return html_files

    html_files = get_html_files(root_directory)

    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    title = SubElement(channel, 'title')
    title.text = 'My RSS Feed'
    link = SubElement(channel, 'link')
    link.text = urlroot
    description = SubElement(channel, 'description')
    description.text = 'This is an RSS feed of my website.'

    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        item_title, pub_date = extract_metadata(html_content)
        url = file_path.replace(root_directory, urlroot + '/').replace('\\', '/').lstrip('/')
        url = url.replace('//', '/')
        url = url.replace('https:/', 'https://')
        url = url.replace(".html", "")

        item = SubElement(channel, 'item')
        item_title_elem = SubElement(item, 'title')
        item_title_elem.text = item_title
        link_elem = SubElement(item, 'link')
        link_elem.text = url
        guid_elem = SubElement(item, 'guid')
        guid_elem.text = url
        if pub_date:
            pub_date_elem = SubElement(item, 'pubDate')
            pub_date_elem.text = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%a, %d %b %Y %H:%M:%S +0000')

    output_file = os.path.join(root_directory, 'rss_feed.xml')
    ElementTree(rss).write(output_file, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    root_directory = input("Enter the root directory of your HTML files: ")
    urlroot = input("Enter the URL root (e.g., https://www.example.com): ")
    generate_rss_feed(root_directory, urlroot)
