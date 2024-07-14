import os
from bs4 import BeautifulSoup

def generate_sitemap(root_directory, urlroot=''):
    def get_html_files(directory):
        html_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.html'):
                    file_path = os.path.join(root, file)
                    html_files.append(file_path)
        return html_files

    def get_canonical_url(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            canonical_link = soup.find('link', rel='canonical')
            if canonical_link and canonical_link.has_attr('href'):
                return canonical_link['href']
        return None

    html_files = get_html_files(root_directory)

    output_file = os.path.join(root_directory, 'sitemap.xml')

    with open(output_file, 'w', encoding='utf-8') as sitemap_file:
        sitemap_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        sitemap_file.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for file_path in html_files:
            print('-------in-----')
            canonical_url = get_canonical_url(file_path)
            print(canonical_url, file_path)
            if canonical_url:
                if not canonical_url.startswith(urlroot):
                    url = (urlroot + canonical_url).replace('//', '/')
                    url = url.replace('https:/', 'https://')
                else:
                    url = canonical_url
            else:
                url = file_path.replace(root_directory, urlroot + '/').replace('\\', '/').lstrip('/')
                url = url.replace('//', '/')
                url = url.replace('https:/', 'https://')
                url = url.replace(".html", "")

            sitemap_file.write(f'  <url>\n')
            sitemap_file.write(f'    <loc>{url}</loc>\n')
            sitemap_file.write(f'  </url>\n')

        sitemap_file.write('</urlset>\n')
