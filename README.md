# MarkdownBlogger - Convert your Markdown into a Website

Welcome to MarkdownBlogger, the simplest framework for creating websites from your Markdown files! With SimplyMarkdown, you can easily and quickly turn your directory of Markdown files into a stunning website without having to deal with any complicated configurations or bloated features.

As a solo developer who enjoys creating fun and easy-to-use tools in my free time, I wanted to make something that was both lightweight and effective. And that's exactly what MarkdownBlogger is all about! It's a simple and straightforward framework that lets you focus on your content, not the technical details.

So whether you're a blogger, writer, or just someone who wants to share their thoughts and ideas with the world, MarkdownBlogger has got you covered. With its intuitive interface and easy-to-use features, you'll be up and running in no time!

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
python3 render.py -i /path/to/directory
```

The output directory will be formed inside the parent folder of the input directory.

Additionally you can use `-t` to set a website title, and -o to specify output location.

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

## Special Tags

I have introduced the `%` tag for easier rendering in SimplyMarkdown. If you use 
```
% <directory>`
```
SimplyMarkdown will render a list of links to all files under that directory. You can see an example usage in the `blog.md` file in `example/input/blog`.

## Github Pages Integration

Using MarkdownBlogger with github pages is very simple. 

1. If you have a website on your github pages repository `<username>/<username>.github.io`, checkout into a new branch and push it there as a backup.
1. Create a new branch on your github pages repository `<username>/<username>.github.io`, named `source`
1. Delete everything in your branch `source`, add the [worklfow](/workflow/render.yaml) into a new directory `.github/workflows`
1. Create a folder in your `source` branch, let's call it `./source`, this is going to act as the root of your markdown directory
1. Populate your markdown directory as needed. **To see an example check out [my personal website](https://github.com/cemreefe/cemreefe.github.io)**.
1. When you push to your source branch, the workflow will trigger, clear out your `main` branch, and populate it with the rendered MarkdownBlogger website based on your source files

