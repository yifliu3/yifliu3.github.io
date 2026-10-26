from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Element:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.content = []

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def descendants(self, tag=None, class_name=None):
        matches = []
        for child in self.children:
            if (
                (tag is None or child.tag == tag)
                and (class_name is None or child.has_class(class_name))
            ):
                matches.append(child)
            matches.extend(child.descendants(tag, class_name))
        return matches

    def text(self):
        return " ".join(
            item.text() if isinstance(item, Element) else item
            for item in self.content
        )


class PageParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.root = Element("document", {})
        self.stack = [self.root]
        self.ids = {}
        self.duplicate_ids = []

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        self.stack[-1].content.append(node)
        node_id = node.attrs.get("id")
        if node_id:
            if node_id in self.ids:
                self.duplicate_ids.append(node_id)
            self.ids[node_id] = node
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].content.append(data)


class HomepageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "stylesheet.css").read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.html)
        cls.root = cls.parser.root

    def test_required_sections_and_anchor_links_exist(self):
        required = {
            "about", "open-source", "projects", "education", "experience",
            "awards", "activities", "miscellaneous",
        }
        sections = self.root.descendants("section")
        self.assertEqual({node.attrs["id"] for node in sections}, required)
        self.assertEqual(self.parser.duplicate_ids, [])
        for link in self.root.descendants("a"):
            href = link.attrs.get("href", "")
            if href.startswith("#"):
                self.assertIn(href[1:], self.parser.ids)
        self.assertNotIn("news", self.parser.ids)

    def test_section_order_preserves_user_content(self):
        expected = [
            "about", "open-source", "projects", "education", "experience",
            "awards", "activities", "miscellaneous",
        ]
        self.assertEqual(
            [node.attrs["id"] for node in self.root.descendants("section")],
            expected,
        )

    def test_profile_uses_yifan_identity(self):
        headings = self.root.descendants("h1")
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].text().strip(), "Yifan Liu")
        for required in (
            "liuyifan365@gmail.com", "Uv7f-HMAAAAJ",
            "https://github.com/yifliu3",
        ):
            self.assertIn(required, self.html)
        self.assertNotIn("Ph.D. Candidate, Electronic Engineering, CUHK", self.html)
        self.assertFalse(self.root.descendants(class_name="page-subtitle"))
        for stale in (
            "liushengyuan@link.cuhk.edu.hk", "zP6fRqcAAAAJ",
            "Saint-lsy/MedPruner", "climba@utexas.edu", "huI5ip8AAAAJ",
            "G-CQVGENQ4WN", "curriculum_vitae3.pdf",
        ):
            self.assertNotIn(stale, self.html)

    def test_template_layout_replaces_cover_and_cards(self):
        for class_name in (
            "about-intro", "profile", "content-wrapper",
            "page-title", "section-heading",
        ):
            self.assertTrue(self.root.descendants(class_name=class_name))
        for obsolete in ("profile-cover", "profile-card", "project-card"):
            self.assertFalse(self.root.descendants(class_name=obsolete))
            self.assertNotIn("." + obsolete, self.css)
        self.assertIn('grid-template-columns: 240px minmax(0, 1fr)', self.css)
        self.assertIn("--content-width: 800px", self.css)
        self.assertIn('grid-template-columns: minmax(0, 1fr) 200px', self.css)
        self.assertFalse(self.root.descendants("nav"))
        self.assertIn('"Lato"', self.css)
        self.assertIn('fonts/lato-regular-latin.woff2', self.html)

    def test_larger_typography_preserves_compact_spacing(self):
        self.assertIn('--font-body: "Lato", Verdana, Helvetica, sans-serif', self.css)
        self.assertIn('--font-head: var(--font-body)', self.css)
        self.assertNotIn('Roboto', self.html + self.css)
        for selector, properties in (
            ("body", ("font-size: 16px", "line-height: normal")),
            (".page-title", ("font-size: 36px", "font-weight: 400")),
            (".section-heading", ("font-size: 24px", "font-weight: 400")),
            (".content-wrapper", ("padding: 20px 0 24px",)),
            (".content-section", ("margin-top: 42px",)),
            (".publication-title", ("font-size: 16px", "line-height: normal")),
            (".publication-authors", ("font-size: 16px", "line-height: normal")),
            (".publication-venue", ("font-size: 16px",)),
            (".resource-link", ("font-size: 16px", "line-height: normal")),
            (".publication-description", ("font-size: 16px", "line-height: normal")),
            (".heading-link", ("font-size: 16px",)),
            (".section-note", ("font-size: 16px",)),
            (".education-content h3", ("font-size: 16px",)),
            (".education-content p", ("font-size: 16px",)),
            (".footer-wrapper", ("font-size: 14px",)),
            (".gh-star-badge", ("font-size: 12px",)),
            (".publication-item", ("padding: 0", "gap: 0")),
        ):
            rule = re.search(
                rf"(?<![\w.-]){re.escape(selector)}\s*\{{([^}}]+)\}}",
                self.css,
            ).group(1)
            for property_text in properties:
                self.assertIn(property_text, rule)

    def test_all_sections_use_uniform_spacing(self):
        desktop_css, mobile_css = self.css.split("@media (max-width: 720px)", 1)
        self.assertRegex(
            desktop_css,
            r"\.content-section\s*\{[^}]*margin-top:\s*42px",
        )
        self.assertNotIn(".content-section {", mobile_css)
        self.assertNotIn("#open-source + #projects", self.css)
        for rules in (desktop_css, mobile_css):
            self.assertRegex(rules, r"\.about-section\s*\{[^}]*margin-top:\s*0")

    def test_publication_spacing_is_larger_with_reference_geometry(self):
        for selector, properties in (
            (".project-list", ("gap: 20px", "margin: 0 -16px")),
            (".publication-item", (
                "grid-template-columns: 240px minmax(0, 1fr)",
                "min-height: 160px", "align-items: center",
            )),
            (".project-media", ("width: 200px", "height: 120px", "margin: 20px")),
            (".project-content", ("padding: 1px",)),
        ):
            rule = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", self.css).group(1)
            for property_text in properties:
                self.assertIn(property_text, rule)
        for selector in (
            ".publication-title", ".publication-authors",
            ".resource-links", ".publication-description",
        ):
            rule = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", self.css).group(1)
            self.assertIn("margin: 0", rule)
        self.assertIn('.publication-title a { color: inherit; }', self.css)
        self.assertIn('.resource-link + .resource-link::before { content: "|"; }', self.css)
        mobile = self.css.split("@media (max-width: 720px)", 1)[1]
        self.assertNotIn(".project-list {", mobile)
        self.assertRegex(mobile, r"\.publication-item\s*\{[^}]*gap:\s*10px")
        self.assertRegex(mobile, r"\.page-title\s*\{[^}]*font-size:\s*36px")
        self.assertIn("aspect-ratio: 5 / 3", mobile)

    def test_reference_font_files_are_local_and_complete(self):
        faces = re.findall(r"@font-face\s*\{([^}]+)\}", self.css)
        self.assertEqual(len(faces), 8)
        for style in ("normal", "italic"):
            for weight in (400, 700):
                matching = [
                    face for face in faces
                    if f"font-style: {style};" in face
                    and f"font-weight: {weight};" in face
                ]
                self.assertEqual(len(matching), 2)
                for face in matching:
                    self.assertIn('font-family: "Lato"', face)
                    self.assertIn("font-display: swap", face)
                    file_name = re.search(r'url\("([^"]+)"\)', face).group(1)
                    self.assertEqual((ROOT / file_name).read_bytes()[:4], b"wOF2")
        self.assertTrue((ROOT / "fonts/OFL.txt").exists())
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertNotIn("fonts.gstatic.com", self.html + self.css)
        self.assertNotIn("-webkit-font-smoothing", self.css)

    def test_all_featured_items_are_preserved(self):
        titles = [
            "Hy-Nomas: Towards Free-Form Interactive World Generation",
            "Hy-World 1.1",
            "WorldMirror: Universal 3D World Reconstruction with Any-Prior Prompting",
            "MonoSplat: Generalizable 3D Gaussian Splatting from Monocular Depth Foundation Models",
            "Foundation Model-guided Gaussian Splatting for 4D Reconstruction of Deformable Tissues",
            "U-KAN Makes Strong Backbone for Medical Image Segmentation and Generation",
        ]
        rendered = self.root.descendants("article", "publication-item")
        self.assertEqual(len(rendered), len(titles))
        for item, title in zip(rendered, titles):
            heading = item.descendants("h3", "publication-title")
            self.assertEqual(len(heading), 1)
            self.assertEqual(heading[0].text().strip(), title)
            self.assertEqual(len(item.descendants(class_name="project-media")), 1)
            self.assertTrue(item.descendants("a", "resource-link"))

    def test_publication_venues_are_text_before_resource_links(self):
        expected = [
            "ICML 2026", "CVPR 2025",
            "IEEE TMI 2025", "AAAI 2025",
        ]
        publications = self.parser.ids["projects"].descendants("article")
        self.assertEqual(len(publications), len(expected))
        for item, venue in zip(publications, expected):
            body = item.descendants(class_name="project-content")[0]
            venue_node = body.descendants("p", "publication-venue")[0]
            links = body.descendants(class_name="resource-links")[0]
            self.assertEqual(venue_node.text().strip(), venue)
            self.assertLess(body.children.index(venue_node), body.children.index(links))
            self.assertFalse(links.descendants(class_name="publication-venue"))
        self.assertNotIn("venue-badge", self.html)

    def test_removed_publications_stay_removed(self):
        self.assertNotIn("GTP-4o: Modality-prompted", self.html)
        self.assertNotIn("FedPD: Federated Open Set Recognition", self.html)
        for removed in (
            "GaussianReg", "pic/IMG_gaussianreg.png",
            "Rapid 2D/3D registration for emergency surgery",
        ):
            self.assertNotIn(removed, self.html)

    def test_instantsplamp_is_removed(self):
        for removed in (
            "InstantSplamp", "pic/instantsplamp.png",
            "https://gaussian-stego.github.io/",
            "https://arxiv.org/abs/2407.01301",
            "https://github.com/CUHK-AIM-Group/GaussianStego",
            "A framework for embedding imperceptible, recoverable information",
        ):
            self.assertNotIn(removed, self.html)

    def test_local_assets_exist(self):
        refs = [
            node.attrs.get("src", "")
            for tag in ("img", "source", "script")
            for node in self.root.descendants(tag)
        ]
        refs.extend(
            node.attrs.get("href", "")
            for node in self.root.descendants("link")
        )
        refs.extend(re.findall(r'url\(["\']?([^)"\']+)', self.css))
        missing = []
        for ref in refs:
            if not ref or ref.startswith(("http://", "https://", "data:")):
                continue
            path = ROOT / ref.split("#", 1)[0].split("?", 1)[0]
            if not path.exists():
                missing.append(ref)
        self.assertEqual(missing, [])

    def test_videos_keep_inline_autoplay_contract(self):
        videos = self.root.descendants("video")
        self.assertEqual(len(videos), 4)
        for video in videos:
            for attribute in ("autoplay", "muted", "loop", "playsinline"):
                self.assertIn(attribute, video.attrs)

    def test_images_and_icon_controls_are_accessible(self):
        for image in self.root.descendants("img"):
            self.assertTrue(image.attrs.get("alt", "").strip())
        for button in self.root.descendants("button"):
            self.assertTrue(button.attrs.get("aria-label", "").strip())
            self.assertTrue(button.attrs.get("title", "").strip())
            self.assertEqual(button.attrs.get("type"), "button")
            icons = button.descendants("i")
            self.assertTrue(icons)
            for icon in icons:
                self.assertEqual(icon.attrs.get("aria-hidden"), "true")
        for link in self.root.descendants("a"):
            if link.attrs.get("target") == "_blank":
                self.assertIn("noopener", link.attrs.get("rel", "").split())

    def test_sections_reference_existing_headings(self):
        for section in self.root.descendants("section"):
            heading_id = section.attrs["aria-labelledby"]
            heading = self.parser.ids[heading_id]
            self.assertIn(heading, section.descendants())

    def test_theme_defaults_to_light_and_preserves_manual_choice(self):
        self.assertIn('<html lang="en" data-theme="light">', self.html)
        self.assertIn("var theme = 'light';", self.html)
        self.assertNotIn('prefers-color-scheme', self.html)
        self.assertNotIn('prefers-color-scheme', self.css)
        self.assertIn('html[data-theme="dark"]', self.css)
        self.assertIn("localStorage.getItem('theme')", self.html)
        self.assertIn("localStorage.setItem('theme', theme)", self.html)
        self.assertIn("try { localStorage.setItem", self.html)
        self.assertLess(
            self.html.index("document.documentElement.setAttribute('data-theme'"),
            self.html.index("<body>"),
        )

    def test_jon_barron_profile_links_and_unframed_rows(self):
        links = self.root.descendants(class_name="social-links")[0].descendants("a")
        self.assertEqual([link.text().strip() for link in links], ["Email", "Google Scholar", "GitHub"])
        for link in links:
            self.assertFalse(link.descendants("i"))
        self.assertIn('content: "/"', self.css)
        self.assertRegex(self.css, r"\.page-title\s*\{[^}]*text-align:\s*center")
        self.assertRegex(self.css, r"\.profile-avatar\s*\{[^}]*border-radius:\s*50%")
        for selector in (".publication-item", ".resource-link", ".project-media"):
            rule = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", self.css).group(1)
            for framed_property in ("border:", "border-bottom:", "box-shadow:", "background:"):
                self.assertNotIn(framed_property, rule)
        self.assertNotIn("menu-toggle", self.html + self.css)

    def test_report_heading_and_online_demo_labels(self):
        self.assertEqual(
            self.parser.ids["open-source-heading"].text().strip(),
            "Technical Report",
        )
        demo_links = [
            link for link in self.root.descendants("a", "resource-link")
            if link.attrs.get("href", "").startswith("https://huggingface.co/spaces/")
        ]
        self.assertEqual(len(demo_links), 2)
        self.assertTrue(all(link.text().strip() == "Online Demo" for link in demo_links))
        self.assertNotIn("Try it now", self.html)
        self.assertNotIn("Open-Source Projects", self.html)

    def test_hy_nomas_report_has_local_preview_and_resource_links(self):
        reports = self.parser.ids["open-source"].descendants("article")
        self.assertEqual(len(reports), 2)
        report = reports[0]
        self.assertEqual(
            report.descendants("h3")[0].text().strip(),
            "Hy-Nomas: Towards Free-Form Interactive World Generation",
        )
        self.assertEqual(
            report.descendants(class_name="publication-authors")[0].text().strip(),
            "Core Contributor",
        )
        self.assertEqual(
            report.descendants(class_name="publication-venue")[0].text().strip(),
            "Technical Report, 2026",
        )
        video = report.descendants("video")[0]
        self.assertEqual(video.attrs["poster"], "pic/hy-nomas-poster.jpg")
        self.assertEqual(video.descendants("source")[0].attrs["src"], "vid/Hy-Nomas.mp4")
        self.assertTrue((ROOT / video.attrs["poster"]).exists())
        links = report.descendants("a", "resource-link")
        self.assertEqual(
            [(link.text().strip(), link.attrs["href"]) for link in links],
            [
                ("Code", "https://github.com/Tencent-Hunyuan/Hy-Nomas"),
                ("Project Page", "https://hy-nomas.hy.tencent.com/"),
                ("Online Demo", "https://hy-nomas.hy.tencent.com/demo"),
            ],
        )
        self.assertEqual(links[0].attrs.get("data-no-stars"), "true")
        self.assertIn(
            "An interactive world generation model that supports free-form, "
            "multi-turn text instructions and camera control.",
            report.text(),
        )

    def test_report_resources_start_with_report_link_or_placeholder(self):
        reports = self.parser.ids["open-source"].descendants("article")
        items = [
            report.descendants(class_name="resource-links")[0].children
            for report in reports
        ]
        for resources in items:
            self.assertEqual(
                [resource.text().strip() for resource in resources],
                ["Report", "Code", "Project Page", "Online Demo"],
            )
        pending = items[0][0]
        self.assertEqual(pending.tag, "span")
        self.assertEqual(pending.attrs.get("aria-disabled"), "true")
        self.assertNotIn("href", pending.attrs)
        self.assertTrue(pending.has_class("resource-link-pending"))
        self.assertIn(".resource-link-pending { color: var(--text-muted); }", self.css)
        report_link = items[1][0]
        self.assertEqual(report_link.tag, "a")
        self.assertEqual(
            report_link.attrs["href"],
            "https://3d-models.hunyuan.tencent.com/world/worldMirror1_0/HYWorld_Mirror_Tech_Report.pdf",
        )

    def test_reports_use_bold_singular_contributor_and_separate_years(self):
        reports = self.parser.ids["open-source"].descendants("article")
        for report, year in zip(reports, (2026, 2025)):
            body = report.descendants(class_name="project-content")[0]
            contributor = body.descendants(class_name="publication-authors")[0]
            venue = body.descendants(class_name="publication-venue")[0]
            links = body.descendants(class_name="resource-links")[0]
            self.assertEqual(contributor.text().strip(), "Core Contributor")
            self.assertEqual(len(contributor.descendants("strong")), 1)
            self.assertEqual(contributor.descendants("strong")[0].text().strip(), "Core Contributor")
            self.assertEqual(venue.text().strip(), f"Technical Report, {year}")
            self.assertLess(body.children.index(contributor), body.children.index(venue))
            self.assertLess(body.children.index(venue), body.children.index(links))
        self.assertNotIn("Core Contributors", self.html)
        self.assertNotIn("Core Contributor, 2025", self.html)
        self.assertNotIn("HY-World 1.1", self.html)

    def test_profile_is_compact_on_desktop_and_mobile(self):
        desktop_css, mobile_css = self.css.split("@media (max-width: 720px)", 1)
        self.assertRegex(desktop_css, r"\.profile\s*\{[^}]*width:\s*200px")
        self.assertRegex(mobile_css, r"\.profile\s*\{[^}]*width:\s*150px")
        self.assertIn("object-fit: contain", self.css)

    def test_dark_mode_uses_blue_accents_and_emphasis(self):
        explicit_dark = re.search(
            r"html\[data-theme=\"dark\"\]\s*\{([^}]+)\}", self.css,
        ).group(1)
        self.assertIn("--accent: #2698ba", explicit_dark)
        self.assertIn("--emphasis-text: var(--accent)", explicit_dark)
        self.assertIn("--accent: #1772d0", self.css)
        self.assertIn("--hover: #f09228", self.css)
        self.assertRegex(self.css, r"strong\s*\{\s*color:\s*var\(--emphasis-text\)")
        self.assertRegex(
            self.css,
            r"\.publication-authors strong\s*\{[^}]*color:\s*var\(--emphasis-text\)",
        )

    def test_responsive_styles_and_reduced_motion(self):
        mobile_css = self.css.split("@media (max-width: 720px)", 1)[1]
        self.assertRegex(
            mobile_css,
            r"\.publication-item\s*\{[^}]*grid-template-columns:\s*1fr",
        )
        self.assertRegex(mobile_css, r"\.profile\s*\{[^}]*grid-row:\s*2")
        self.assertRegex(mobile_css, r"\.about-body\s*\{[^}]*grid-row:\s*3")
        self.assertRegex(mobile_css, r"\.social-links\s*\{[^}]*grid-row:\s*4")
        self.assertIn("width: min(200px, calc(100% - 40px))", mobile_css)
        self.assertIn("minmax(0, 1fr)", mobile_css)
        self.assertIn("overflow-wrap: break-word", self.css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn("scroll-behavior: auto", self.css)
        self.assertIn("reducedMotion ? 'instant' : 'smooth'", self.html)
        self.assertNotIn("overflow-x: hidden", self.css)

    def test_progressive_enhancements_are_preserved(self):
        for node_id in (
            "backToTop", "visitCounter", "visitCount",
            "mediaPreview", "mediaPreviewFrame",
        ):
            self.assertIn(node_id, self.parser.ids)
        self.assertIn("abacus.jasoncameron.dev", self.html)
        self.assertIn("matchMedia('(hover: none)')", self.html)
        self.assertNotIn("updateActiveSection", self.html)

    def test_github_stars_use_generated_same_origin_data(self):
        self.assertIn("fetch('data/github-stars.json'", self.html)
        self.assertNotIn("api.github.com", self.html)
        stars = json.loads((ROOT / "data/github-stars.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(stars),
            {
                "Tencent-Hunyuan/HunyuanWorld-Mirror",
                "CUHK-AIM-Group/MonoSplat", "CUHK-AIM-Group/GaussianStego",
                "CUHK-AIM-Group/EndoGaussian", "CUHK-AIM-Group/U-KAN",
                "CUHK-AIM-Group/GaussianReg",
            },
        )
        self.assertTrue(all(isinstance(count, int) and count >= 0 for count in stars.values()))
        workflow = (ROOT / ".github/workflows/update-github-stars.yml").read_text(encoding="utf-8")
        for marker in (
            "schedule:", "workflow_dispatch:", "pages: write",
            "python3 scripts/update_github_stars.py",
            "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4",
        ):
            self.assertIn(marker, workflow)
        code_links = [
            link for link in self.parser.ids["projects"].descendants("a", "resource-link")
            if link.attrs.get("href", "").startswith("https://github.com/")
        ]
        self.assertEqual(len(code_links), 4)
        project_link = self.parser.ids["open-source"].descendants("a", "resource-link")[0]
        self.assertEqual(project_link.attrs.get("data-no-stars"), "true")

    def test_optional_network_and_storage_failures_are_non_fatal(self):
        self.assertGreaterEqual(self.html.count(".catch(function () {"), 2)
        self.assertIn("try { counted = sessionStorage.getItem", self.html)
        self.assertIn("try { sessionStorage.setItem", self.html)

    def test_about_describes_research_and_collaboration(self):
        section = self.parser.ids["about"]
        about = " ".join(section.text().split())
        about = re.sub(r"\s+([,.])", r"\1", about)
        for text in (
            "I am a Researcher at Tencent HY",
            "working with Dr. Heng Wang in the Video World Foundation Model Team.",
            "Previously, I received my Ph.D. in Electronic Engineering from the Chinese University "
            "of Hong Kong, advised by Prof. Yixuan Yuan.",
            "During my Ph.D., I have been fortunate to work with",
            "My research focuses on video generation, world models, and 3D vision, with an emphasis "
            "on building practical products for generation and understanding in real-world applications.",
            "Dr. Zhenwei Wang",
            "Dr. Tengfei Wang", "Tencent HY 3D Generation Team",
        ):
            self.assertIn(text, about)
        heng_links = [
            link for link in section.descendants("a")
            if link.text().strip() == "Dr. Heng Wang"
        ]
        self.assertEqual(len(heng_links), 1)
        self.assertEqual(heng_links[0].attrs["href"], "https://hengcv.github.io/")
        advisor_links = [
            link for link in section.descendants("a")
            if link.text().strip() == "Prof. Yixuan Yuan"
        ]
        self.assertEqual(len(advisor_links), 1)
        self.assertEqual(advisor_links[0].attrs["href"], "https://www.ee.cuhk.edu.hk/~yxyuan/")
        for removed in (
            "final-year Ph.D. student",
            "B.Eng.", "ByteDance Seed",
        ):
            self.assertNotIn(removed, about)
        self.assertIn('href="mailto:liuyifan365@gmail.com">contact me</a>', self.html)

    def test_about_emphasizes_company_and_research_interests(self):
        emphasis = [
            node.text().strip()
            for node in self.parser.ids["about"].descendants("strong")
        ]
        self.assertEqual(emphasis.count("Tencent HY"), 2)
        self.assertIn("video generation, world models, and 3D vision", emphasis)

    def test_institution_names_are_plain_text(self):
        names = (
            "Tencent HY", "Chinese University of Hong Kong",
            "Huazhong University of Science and Technology",
        )
        for link in self.root.descendants("a"):
            label = " ".join(link.text().split())
            for name in names:
                self.assertNotIn(name, label)
        for school in self.parser.ids["education"].descendants(class_name="education-school"):
            self.assertFalse(school.descendants("a"))
        self.assertIn('href="https://hengcv.github.io/">Dr. Heng Wang</a>', self.html)
        self.assertIn('href="https://zhenwwang.github.io/">Dr. Zhenwei Wang</a>', self.html)
        self.assertIn('href="https://tengfei-wang.github.io/">Dr. Tengfei Wang</a>', self.html)
        self.assertIn('href="https://www.ee.cuhk.edu.hk/~yxyuan/">Prof. Yixuan Yuan</a>', self.html)

    def test_education_and_experience_are_preserved(self):
        education = self.parser.ids["education"]
        self.assertEqual(len(education.descendants("article", "education-item")), 2)
        for text in (
            "The Chinese University of Hong Kong (CUHK)",
            "Ph.D. in Electronic Engineering", "2021–2026",
            "Huazhong University of Science and Technology (HUST)",
            "B.Eng. in Electronic Information Engineering", "2017–2021",
            "Advisor:",
        ):
            self.assertIn(text, education.text())
        self.assertEqual(len(education.descendants("img")), 2)
        experience = self.parser.ids["experience"]
        self.assertEqual(len(experience.descendants("li")), 2)
        for text in ("Research Intern", "Tencent HY", "Video World Foundation Model Team", "3D Generation Team"):
            self.assertIn(text, experience.text())
        self.assertNotIn("Video World Model Team", experience.text())

    def test_services_honors_and_interests_are_preserved(self):
        services = self.parser.ids["activities"].text()
        self.assertIn("CVPR, ICCV, ECCV, NeurIPS, ICLR, ICML, ICRA, IROS", services)
        self.assertIn("TPAMI, IJCV, TVCG, TNNLS, TCSVT, TMM, TMI, MIA", services)
        honors = self.parser.ids["awards"].descendants("li")
        self.assertEqual(len(honors), 5)
        self.assertEqual(honors[0].text().strip(), "Golden Reviewer Award, ICML 2026")
        self.assertEqual(
            [honor.text().strip() for honor in honors][2:4],
            ["Outstanding Graduates, HUST, 2021", "First Class Scholarship, 2019–2020"],
        )
        self.assertNotIn(
            "Outstanding Graduates of Huazhong University of Science and Technology",
            self.html,
        )
        self.assertIn("Postgraduate Studentship, CUHK, 2021–2026", self.html)
        self.assertIn("First Class Scholarship, 2019–2020", self.html)
        self.assertNotIn("Self-Reliance Scholarship", self.html)
        interests = self.parser.ids["miscellaneous"].text()
        for interest in ("basketball", "swimming", "table tennis", "badminton"):
            self.assertIn(interest, interests)
        self.assertNotIn("hiking", interests)
        self.assertNotIn("\u26f0", interests)

    def test_footer_credits_current_template(self):
        footer = self.root.descendants("footer")[0]
        self.assertEqual(footer.parent.tag, "body")
        self.assertIn("Website template by", footer.text())
        self.assertIn("Jon Barron", footer.text())
        self.assertIn(
            "https://github.com/jonbarron/jonbarron.github.io",
            [link.attrs["href"] for link in footer.descendants("a")],
        )
        self.assertNotIn("Shengyuan Liu, Jun Cen and Zeqing Yuan", footer.text())
        self.assertNotIn("Hyunsoo Kim", footer.text())


if __name__ == "__main__":
    unittest.main()
