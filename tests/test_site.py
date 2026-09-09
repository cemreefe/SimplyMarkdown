from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from simplymarkdown import BuildConfig, BuildError, SiteBuilder


class SiteBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.output = self.root / "public"
        self.source.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def build(self, **overrides: object):
        options = {
            "input_dir": self.source,
            "output_dir": self.output,
            "root_url": "https://example.com/notes",
            "title": "Notes",
        }
        options.update(overrides)
        return SiteBuilder(BuildConfig(**options)).build()

    def test_example_build_is_complete_and_uses_one_url_model(self) -> None:
        shutil.rmtree(self.source)
        example = Path(__file__).parents[1] / "example/input"
        shutil.copytree(example, self.source)

        result = self.build()

        self.assertEqual(7, len(result.pages))
        index = (self.output / "index.html").read_text(encoding="utf-8")
        blog = (self.output / "blog.html").read_text(encoding="utf-8")
        post = (self.output / "posts/2023/02/18/Hogwarts-Legacy.html").read_text(encoding="utf-8")
        self.assertIn("<title>Home · Notes</title>", index)
        self.assertIn('href="/notes/"', index)
        self.assertIn('src="/notes/posts/2023/02/18/example_photo.jpeg"', blog)
        self.assertNotIn('src="///', blog)
        self.assertIn('<span class="categoryTag">gaming</span>', post)

        sitemap = ET.parse(self.output / "sitemap.xml")
        locations = {node.text for node in sitemap.findall("{*}url/{*}loc")}
        self.assertIn("https://example.com/notes/", locations)
        self.assertIn("https://example.com/notes/about", locations)
        self.assertTrue(all(location.startswith("https://") for location in locations))

        rss = ET.parse(self.output / "rss.xml")
        self.assertEqual("Notes", rss.findtext("channel/title"))
        hogwarts = next(
            item
            for item in rss.findall("channel/item")
            if item.findtext("title") == "Hogwarts Legacy"
        )
        self.assertIn(
            'src="https://example.com/notes/posts/2023/02/18/example_photo.jpeg"',
            hogwarts.findtext("description"),
        )
        self.assertEqual(
            "Mon, 03 Jul 2023 00:00:00 GMT",
            next(
                item.findtext("pubDate")
                for item in rss.findall("channel/item")
                if item.findtext("title") == "Creative Coding"
            ),
        )

    def test_collections_compose_filters_and_render_safe_previews(self) -> None:
        self.write("index.md", "# Index\n\n% posts:detailed:featured:#coding")
        self.write(
            "posts/2025/01/02/keep.md",
            "---\nfeatured: true\ntags: coding\n      design\npreview_shape: arch\n---\n"
            "<parsers-ignore>Language selector</parsers-ignore>\n\n"
            "# Keep\n\n[TOC]\n\n## Details\n\n[Inside](other.html)\n\n"
            "<script>unsafePreview()</script>\n\n<style>.preview { color: red; }</style>",
        )
        self.write(
            "posts/2025/01/01/drop.md",
            "---\nfeatured: false\ntags: coding\n---\n# Drop",
        )

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("Keep", index)
        self.assertNotIn("Drop", index)
        self.assertIn('class="postPreview postPreview--arch postPreview--featured"', index)
        self.assertEqual(1, index.count('class="previewHref"'))
        preview = index.split('class="previewHref"', 1)[1].split("</article>", 1)[0]
        self.assertNotIn("<a href=", preview)
        self.assertNotIn("Language selector", preview)
        self.assertNotIn('class="toc"', preview)
        self.assertNotIn("unsafePreview", preview)
        self.assertNotIn("color: red", preview)

    def test_featured_posts_can_be_ordered_and_the_rest_rendered_separately(self) -> None:
        self.write(
            "index.md",
            "# Index\n\n% posts:detailed:featured\n\n## Rest\n\n% posts:detailed:rest",
        )
        self.write("posts/a.md", "---\nfeatured: 2\ndate: 2025-01-01\n---\n# A")
        self.write("posts/b.md", "---\nfeatured: 1\ndate: 2024-01-01\n---\n# B")
        self.write("posts/c.md", "---\nfeatured: true\ndate: 2026-01-01\n---\n# C")
        self.write("posts/d.md", "---\ndate: 2023-01-01\n---\n# D")

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        featured_html, rest_html = index.split(">Rest<", 1)
        # Ordered featured posts (B, A) come first by their explicit position,
        # then unordered featured posts (C) by recency.
        self.assertLess(featured_html.index(">B<"), featured_html.index(">A<"))
        self.assertLess(featured_html.index(">A<"), featured_html.index(">C<"))
        self.assertNotIn(">D<", featured_html)
        # The rest collection has exactly the non-featured post.
        self.assertIn(">D<", rest_html)
        self.assertNotIn(">A<", rest_html)
        self.assertNotIn(">B<", rest_html)
        self.assertNotIn(">C<", rest_html)

    def test_featured_and_rest_are_mutually_exclusive(self) -> None:
        self.write("index.md", "# Index\n\n% posts:featured:rest")
        self.write("posts/a.md", "# A")

        with self.assertRaisesRegex(BuildError, "mutually exclusive"):
            self.build()

    def test_a_single_page_can_be_referenced_as_its_own_collection(self) -> None:
        self.write("index.md", "# Index\n\n% posts/only.md:detailed")
        self.write("posts/only.md", "---\ndate: 2025-06-01\n---\n# Only\n\nBody text.")

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("Only", index)
        self.assertEqual(1, index.count('class="previewHref"'))

    def test_single_page_reference_rejects_filters(self) -> None:
        self.write("index.md", "# Index\n\n% posts/only.md:detailed:featured")
        self.write("posts/only.md", "# Only")

        with self.assertRaisesRegex(BuildError, "single page reference"):
            self.build()

    def test_grouped_collection_keeps_years_with_their_posts(self) -> None:
        self.write("index.md", "# Index\n\n% posts:grouped")
        self.write("posts/new.md", "---\ndate: 2025-01-09\ntags: coding\n---\n# New")
        self.write("posts/old.md", "---\ndate: 2024-12-31\n---\n# Old")

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="postYearGroup"', index)
        self.assertIn('class="postYearEntries"', index)
        self.assertIn('datetime="2025-01-09"', index)
        self.assertIn(">coding<", index)
        self.assertLess(index.index(">2025<"), index.index("New"))
        self.assertLess(index.index(">2024<"), index.index("Old"))

    def test_detailed_collections_cap_previews_at_one_image(self) -> None:
        self.write("index.md", "# Index\n\n% posts:detailed")
        self.write(
            "posts/post.md",
            "---\nfeatured: true\n---\n# Post\n\n"
            "![one](one.png)\n<small>Image description</small>\n\n"
            "![two](two.png)\n\ntext\n\n![three](three.png)",
        )

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        preview = index.split('class="previewHref"', 1)[1].split("</article>", 1)[0]
        self.assertEqual(1, preview.count("<img"))
        self.assertIn("one.png", preview)
        self.assertNotIn("two.png", preview)
        self.assertNotIn("three.png", preview)
        self.assertIn('alt=""', preview)
        self.assertNotIn("Image description", preview)

    def test_detailed_collections_reject_unknown_preview_shapes(self) -> None:
        self.write("index.md", "# Index\n\n% posts:detailed")
        self.write("posts/post.md", "---\npreview_shape: starburst\n---\n# Post")

        with self.assertRaisesRegex(BuildError, "invalid preview_shape 'starburst'"):
            self.build()

    def test_links_modules_and_html_pages_are_resolved_at_the_site_boundary(self) -> None:
        self.write("modules/navbar.md", "[Home](/index.html)")
        self.write("index.md", "! include callout\n\n[About](about.md)\n\n![Photo](img one.png)")
        self.write("modules/callout.md", "**Reusable.**")
        self.write("about.md", "About without a heading.")
        self.write("legacy.html", "<convertsm>\n# Legacy")
        (self.source / "img one.png").write_bytes(b"image")

        self.build()

        index = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("<strong>Reusable.</strong>", index)
        self.assertIn('href="/notes/about"', index)
        self.assertIn('src="/notes/img%20one.png"', index)
        self.assertIn('href="/notes/"', index)
        self.assertTrue((self.output / "legacy.html").is_file())
        about = (self.output / "about.html").read_text(encoding="utf-8")
        self.assertIn("<title>About without a heading. · Notes</title>", about)

    def test_metadata_is_escaped_without_escaping_rendered_markdown(self) -> None:
        self.write(
            "index.md",
            '---\ntitle: Rock & "Roll" <Site>\ndescription: A & B\n---\n'
            '**Rendered**\n\n<script data-private="yes">alert(1)</script>',
        )

        self.build()

        page = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Rock &amp; &#34;Roll&#34; &lt;Site&gt; · Notes</title>", page)
        self.assertIn('content="A &amp; B"', page)
        self.assertIn("<strong>Rendered</strong>", page)
        self.assertIn("<script", page)
        ET.parse(self.output / "sitemap.xml")
        feed = (self.output / "rss.xml").read_text(encoding="utf-8")
        self.assertNotIn("data-private", feed)

    def test_build_is_clean_and_failure_preserves_the_previous_site(self) -> None:
        self.write("index.md", "# Home")
        old = self.write("old.md", "# Old")
        self.build()
        self.assertTrue((self.output / "old.html").exists())

        old.unlink()
        self.build()
        self.assertFalse((self.output / "old.html").exists())
        previous = (self.output / "index.html").read_bytes()

        self.write("index.md", "! include missing")
        with self.assertRaisesRegex(BuildError, "unknown module"):
            self.build()
        self.assertEqual(previous, (self.output / "index.html").read_bytes())

    def test_validation_rejects_bad_boundaries_and_dates(self) -> None:
        self.write("index.md", "# Home")
        with self.assertRaisesRegex(BuildError, "must not overlap"):
            self.build(output_dir=self.source / "public")
        with self.assertRaisesRegex(BuildError, "absolute http"):
            self.build(root_url="example.com")
        self.write("bad.md", "---\ndate: someday\n---\n# Bad")
        with self.assertRaisesRegex(BuildError, "invalid ISO date"):
            self.build()

    def test_missing_collections_and_empty_sites_fail_loudly(self) -> None:
        self.write("index.md", "# Home\n\n% missing")
        with self.assertRaisesRegex(BuildError, "collection directory does not exist"):
            self.build()
        (self.source / "index.md").unlink()
        with self.assertRaisesRegex(BuildError, "no Markdown pages"):
            self.build()

    def test_extensions_are_small_functions_over_the_shared_page_graph(self) -> None:
        self.write("index.md", "# Home\n\n{{ build-mark }}\n\n% posts:detailed")
        self.write("posts/2026/01/01/extended.md", "# Extended\n\n{{ build-mark }}")

        def markdown_transform(context, page, source):
            return source.replace("{{ build-mark }}", f"There are {len(context.pages)} pages.")

        def html_transform(context, page, rendered):
            return rendered + '\n<img src="extension.png"><!-- transformed -->'

        def artifact(context):
            return {PurePosixPath("robots.txt"): f"Sitemap: {context.root_url}/sitemap.xml\n"}

        result = SiteBuilder(
            BuildConfig(self.source, self.output, "https://example.com/notes", "Notes"),
            markdown_transforms=(markdown_transform,),
            html_transforms=(html_transform,),
            artifact_generators=(artifact,),
        ).build()

        self.assertEqual(2, len(result.pages))
        page = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(page.count("There are 2 pages."), 2)
        self.assertIn("<!-- transformed -->", page)
        self.assertIn('src="/notes/extension.png"', page)
        self.assertEqual(
            "Sitemap: https://example.com/notes/sitemap.xml\n",
            (self.output / "robots.txt").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
