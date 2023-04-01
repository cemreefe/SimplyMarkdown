# SimplyMarkdown

SimplyMarkdown is a simple markdown to html website renderer.

# Setup

Clone the repository

# How to use

## How to run

You can create a new directory with your desired structure to form your website. See example input directory in `/example`.

```
example/input/
├── about.md
├── blog
│   ├── blog.md
│   └── posts
│       ├── coding.md
│       └── hogwarts.md
├── index.md
├── navbar.md
└── static
```

This will form the basis of your website. In the output directory, the tree structure will be kept and all markdown files are going to be rendered into html files according to the template.


Here, `navbar.md` and `static` are reserved names for specific purposes. 
- `navbar.md` will be used to render the navigation bar for all html files. 
- `static` will be used for holding static files to be served, like media, css, js and downloadable content.

To render your website, simply run 

```
python3 render.py /path/to/directory
```

The output directory will be formed inside the parent folder of the input directory.

## Templates

Templates are html files that you supply to set the style of your website's pages. SimplyMarkdown uses a simple junja template as a MVP.

```
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Rendered Markdown</title>
  </head>
  <body>
    <nav>
      {{ navbar }}
    </nav>
    <div class="content">
      {{ content }}
    </div>
  </body>
</html>
```

Where the `{{ navbar }}` is going to be replaced by the rendered `navbar.md` and `{{ content }}` will be replaced by the rendered markdown files specific to pages.