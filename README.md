# SimplyMarkdown - Convert your Markdown into a Website

Welcome to SimplyMarkdown, the simplest framework for creating websites from your Markdown files! With SimplyMarkdown, you can easily and quickly turn your directory of Markdown files into a stunning website without having to deal with any complicated configurations or bloated features.

As a solo developer who enjoys creating fun and easy-to-use tools in my free time, I wanted to make something that was both lightweight and effective. And that's exactly what SimplyMarkdown is all about! It's a simple and straightforward framework that lets you focus on your content, not the technical details.

So whether you're a blogger, writer, or just someone who wants to share their thoughts and ideas with the world, SimplyMarkdown has got you covered. With its easy-to-setup environment, you'll be up and running in no time!

# Setup

To setup SimplyMarkdown locally, the only thing you need to do is to clone the repository. Read further for automated github pages integration.

# How to use

## How to run

You can create a new directory with your desired structure to form your website. See example input directory in `/example`.

```
example/input/
├── about.md
├── index.md
├── blog/
│   ├── blog.md
│   └── posts/
│       ├── coding.md
│       └── hogwarts.md
├── modules/
│   ├── navbar.md
│   ├── footer.md
│   ├── custom-module.md
│   ├── head_extras.html
└── static/
│   ├── images/
│   ├── css/
```

This will form the basis of your website. SimplyMarkdown will clone your directory and process each file to form your website. Markdown files will be rendered as html files.


In SimplyMarkdown, `modules/` is a reserved directory. 
- `modules/navbar.md` will be used to render the navigation bar for all html files. 
- `modules/footer.md` will be used to render the footer for all html files.
- `modules/head_extras.html` can be used to add extra tags to the `<head>` section of your website.
- You can create your own custom modules under the `modules/` directory. To render a custom module in a web page, just inclue the module in your markdown sourcefile such as `! include custom-module` to include `modules/custom-module.md`. 

To render your website, simply run 

```
python3 render.py -i /path/to/directory -o /path/to/output/directory
```

The following command line arguments are available for this script:

- **-i, --input**: Input directory path (required)
- **-o, --output**: Output directory path (required)
- **--css**: CSS to include (default: 'themes/basic.css')
- **--template**: Path to the HTML template (default: 'templates/base.html')
- **--favicon**: Favicon emoji (default: '👤')
- **--root**: Project URL root, this is almost always the CNAME of your domain i.e. `https://myblog.com`. (default: '')
- **--title**: Website title (default: '')

## Special Tags

I have introduced the `%` tag for easier rendering in SimplyMarkdown. If you use 

```
% <relative-directory>`
```

SimplyMarkdown will render a list of links to all files under that directory. You can see an example usage in the `blog.md` file in `example/input/blog`.

If you are in `misc/archive.md`, use `% posts` to list md files in `misc/posts` and its subdirectories. 

If you want detailed post overviews rahter than only titles, use 

```
% <relative-directory>:detailed
```

## Frontmatter

SimplyMarkdown supports frontmatter for markdown files. You can use the following syntax:

```
---
title: <meta title>
emoji: <overview emoji>
date:  <post date>
tags:  <category-tag-1>
       <category-tag-2>
image: <img path>
---

# Your title

Your post
```

If you use the emoji tag an emoji will be shown alongside your posts in non-detailed overview mode.
Date metadata helps sort and date your posts on overview.
Tags add category tags to the top of your page.
Title helps you override the metadata title property for your page if page title is too long.
Image helps you override the metadata image tag of your page. If you don't use this property `static/img/default_img.png` will be used.

## Github Pages Integration

Using SimplyMarkdown with github pages is very simple. 

1. If you have a website on your github pages repository `<username>/<username>.github.io`, checkout into a new branch called `backup` and push your blog there as backup.
1. Create a new branch on your github pages repository `<username>/<username>.github.io`, named `gh-pages`
1. On `main` branch, add the SimplyMarkdown rendering [worklfow](/workflow/render.yaml) into a new directory called `.github/workflows`
1. Create a folder in your `main` branch, call it `source`, this is going to act as the root of your website.
1. Populate your markdown directory as you wish. **To see an example check out [my personal website](https://github.com/cemreefe/cemreefe.github.io)**.
1. When you push to your `main` branch, SimplyMarkdown workflow will trigger, and update your `gh-pages` branch.



## Templates

Templates are html files that you supply to set the style of your website's pages. SimplyMarkdown the following junja template. You can create your own template if desired. However this is rarely necessary.
