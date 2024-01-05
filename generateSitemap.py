import os

def generate_sitemap(root_directory, urlroot=''):
    def get_html_files(directory):
        html_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.html'):
                    file_path = os.path.join(root, file)
                    html_files.append(file_path)
        return html_files

    html_files = get_html_files(root_directory)

    output_file = os.path.join(root_directory, 'sitemap.xml')

    with open(output_file, 'w') as sitemap_file:
        sitemap_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        sitemap_file.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for file_path in html_files:
            url = file_path.replace(root_directory, urlroot + '/').replace('\\', '/').lstrip('/')
            url = url.replace('//', '/')
            url = url.replace('https:/', 'https://')
            if url == urlroot + '/index.html':
                url = urlroot
            sitemap_file.write(f'  <url>\n')
            sitemap_file.write(f'    <loc>{url}</loc>\n')
            sitemap_file.write(f'  </url>\n')

        sitemap_file.write('</urlset>\n')
