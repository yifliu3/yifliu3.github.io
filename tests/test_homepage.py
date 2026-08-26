from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "index.html"
CSS_PATH = ROOT / "stylesheet.css"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.images = []
        self.videos = []
        self.links = []
        self.sources = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "img":
            self.images.append(values)
        elif tag == "video":
            self.videos.append(values)
        elif tag == "a":
            self.links.append(values)
        elif tag == "source":
            self.sources.append(values)


class HomepageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.css = CSS_PATH.read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.html)

    def test_required_sections_exist(self):
        required = {
            "about",
            "experience",
            "open-source",
            "projects",
            "activities",
            "awards",
            "miscellaneous",
        }
        self.assertEqual(required - self.parser.ids, set())
        self.assertNotIn("news", self.parser.ids)
        self.assertNotIn('href="#news"', self.html)
        self.assertIn(
            '<i class="fa-solid fa-cubes" aria-hidden="true"></i> Open-Source Projects',
            self.html,
        )

    def test_profile_uses_yifan_identity(self):
        self.assertIn("Yifan Liu", self.html)
        self.assertIn("liuyifan365@gmail.com", self.html)
        self.assertIn("Uv7f-HMAAAAJ", self.html)
        for stale in (
            "liushengyuan@link.cuhk.edu.hk",
            "zP6fRqcAAAAJ",
            "Saint-lsy/MedPruner",
            "PhD student @CUHK",
        ):
            self.assertNotIn(stale, self.html)

    def test_publication_venues_use_abbreviations(self):
        venues = re.findall(
            r'<p class="publication-venue">([^<]+)</p>',
            self.html,
        )
        self.assertEqual(
            venues,
            [
                "ICML 2026",
                "CVPR 2025",
                "ICLR 2025",
                "IEEE TMI 2025",
                "AAAI 2025",
                "ICCV 2025",
            ],
        )

    def test_publication_venues_are_inside_resource_link_rows(self):
        publications = re.search(
            r'<section id="projects"[\s\S]*?</section>',
            self.html,
        ).group(0)
        resource_rows = re.findall(
            r'<div class="resource-links">([\s\S]*?)</div>',
            publications,
        )
        self.assertEqual(len(resource_rows), 6)
        for row in resource_rows:
            self.assertRegex(
                row,
                r'class="resource-link"[\s\S]*class="publication-venue"',
            )

    def test_removed_publications_are_not_rendered(self):
        self.assertNotIn(
            "GTP-4o: Modality-prompted Heterogeneous Graph Learning "
            "for Omni-modal Biomedical Representation",
            self.html,
        )
        self.assertNotIn(
            "FedPD: Federated Open Set Recognition with Parameter Disentanglement",
            self.html,
        )

    def test_publications_do_not_show_media_venue_badges(self):
        self.assertNotIn('class="venue-badge"', self.html)
        self.assertNotIn(".venue-badge", self.css)

    def test_template_credit_is_present(self):
        self.assertIn(
            "<p>The style of this website is borrowed from "
            "Shengyuan Liu, Jun Cen and Zeqing Yuan</p>",
            self.html,
        )
        self.assertNotIn("Style adapted from", self.html)

    def test_local_assets_exist(self):
        refs = []
        refs.extend(image.get("src", "") for image in self.parser.images)
        refs.extend(source.get("src", "") for source in self.parser.sources)
        refs.extend(re.findall(r'url\(["\']?([^)"\']+)', self.css))
        missing = []
        for ref in refs:
            if not ref or ref.startswith(("http://", "https://", "data:")):
                continue
            path = ROOT / ref.split("#", 1)[0].split("?", 1)[0]
            if not path.exists():
                missing.append(ref)
        self.assertEqual(missing, [])

    def test_page_uses_approved_layout_classes(self):
        for class_name in (
            "site-nav",
            "profile-cover",
            "profile-card",
            "content-wrapper",
            "section-heading",
        ):
            self.assertRegex(self.html, rf'class="[^"]*\b{class_name}\b')

    def test_all_featured_items_are_cards(self):
        expected_titles = (
            "HY-World 1.1",
            "WorldMirror: Universal 3D World Reconstruction with Any-Prior Prompting",
            "MonoSplat: Generalizable 3D Gaussian Splatting from Monocular Depth Foundation Models",
            "InstantSplamp: Fast and Generalizable Stenography Framework for Generative Gaussian Splatting",
            "Foundation Model-guided Gaussian Splatting for 4D Reconstruction of Deformable Tissues",
            "U-KAN Makes Strong Backbone for Medical Image Segmentation and Generation",
            "GaussianReg: Rapid 2D/3D Registration for Emergency Surgery via Explicit 3D Modeling with Gaussian Primitives",
        )
        self.assertEqual(self.html.count('class="project-card"'), len(expected_titles))
        for title in expected_titles:
            self.assertIn(title, self.html)

    def test_project_media_and_card_styles_are_responsive(self):
        self.assertIn(".project-card", self.css)
        self.assertIn(
            "grid-template-columns: minmax(220px, 29%) minmax(0, 1fr)",
            self.css,
        )
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.project-card"
            r"[\s\S]*?grid-template-columns:\s*1fr",
        )

    def test_videos_keep_inline_autoplay_contract(self):
        self.assertGreaterEqual(len(self.parser.videos), 3)
        for video in self.parser.videos:
            for attribute in ("autoplay", "muted", "loop", "playsinline"):
                self.assertIn(attribute, video)

    def test_images_have_alt_text(self):
        missing = [
            image.get("src")
            for image in self.parser.images
            if not image.get("alt", "").strip()
        ]
        self.assertEqual(missing, [])

    def test_blank_target_links_are_safe(self):
        unsafe = []
        for link in self.parser.links:
            if (
                link.get("target") == "_blank"
                and "noopener" not in link.get("rel", "").split()
            ):
                unsafe.append(link.get("href"))
        self.assertEqual(unsafe, [])

    def test_progressive_enhancements_are_present(self):
        required = (
            'id="backToTop"',
            'id="visitCounter"',
            'id="visitCount"',
            'id="mediaPreview"',
            'id="mediaPreviewFrame"',
            "gh-star-cache-v1",
            "abacus.jasoncameron.dev",
            "matchMedia('(hover: none)')",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_api_failures_are_non_fatal(self):
        self.assertGreaterEqual(
            self.html.count(".catch(function () {"),
            2,
            "Both visit and GitHub API requests must handle rejection",
        )

    def test_mobile_css_prevents_horizontal_overflow(self):
        self.assertRegex(self.css, r"body\s*\{[\s\S]*?overflow-x:\s*hidden")
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.menu-toggle"
            r"\s*\{[\s\S]*?width:\s*100%",
        )
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.about-body p"
            r"\s*\{[\s\S]*?text-align:\s*left",
        )
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.content-wrapper"
            r"\s*\{[\s\S]*?max-width:\s*calc\(100vw - 30px\)",
        )

    def test_about_describes_research_and_collaboration(self):
        required = (
            "Tencent HY and ByteDance Seed",
            "video and 3D world models",
            "3D reconstruction",
            "generative AI",
            'href="mailto:liuyifan365@gmail.com">contact me</a>',
        )
        for text in required:
            self.assertIn(text, self.html)
        self.assertRegex(
            self.html,
            r"Tencent HY</a> 3D Generation Team\.\s+"
            r"I have also been fortunate to collaborate with industry, "
            r"particularly with Tencent HY and ByteDance Seed\.\s*</p>",
        )
        self.assertNotIn(">Tencent Hunyuan<", self.html)
        self.assertEqual(self.html.count(">Tencent HY</a>"), 3)
        self.assertRegex(
            self.css,
            r"\.about-body p \+ p\s*\{[\s\S]*?margin-top:\s*15px",
        )

    def test_education_section_lists_cuhk_and_hust(self):
        self.assertIn("education", self.parser.ids)
        self.assertIn('href="#education"', self.html)
        required = (
            "The Chinese University of Hong Kong (CUHK)",
            "Ph.D. in Electronic Engineering",
            "Huazhong University of Science and Technology (HUST)",
            "B.Eng. in Electronic Information Engineering",
            'src="images/education/cuhk.png"',
            'src="images/education/hust.png"',
        )
        for text in required:
            self.assertIn(text, self.html)
        self.assertEqual(self.html.count('class="education-item"'), 2)
        self.assertIn('class="education-school"', self.html)
        self.assertIn('class="education-detail">Advisor:', self.html)
        self.assertRegex(
            self.css,
            r"\.education-item\s*\{[\s\S]*?display:\s*flex"
            r"[\s\S]*?align-items:\s*center",
        )
        self.assertRegex(
            self.css,
            r"\.education-logo\s*\{[\s\S]*?width:\s*56px"
            r"[\s\S]*?height:\s*56px[\s\S]*?background:\s*#f5f5f5"
            r"[\s\S]*?border-radius:\s*8px",
        )
        education_item_rule = re.search(
            r"\.education-item\s*\{(?P<body>[\s\S]*?)\}",
            self.css,
        )
        self.assertIsNotNone(education_item_rule)
        self.assertNotIn("border-bottom", education_item_rule.group("body"))
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.education-item"
            r"\s*\{[\s\S]*?gap:\s*18px",
        )

    def test_vertical_rhythm_matches_reference_template(self):
        self.assertRegex(
            self.css,
            r"body\s*\{[\s\S]*?font:\s*300 16px/1\.5 ",
        )
        self.assertRegex(
            self.css,
            r"\.content-wrapper\s*\{[\s\S]*?padding:\s*30px 0 56px",
        )
        self.assertRegex(
            self.css,
            r"\.content-section\s*\{[\s\S]*?margin:\s*10px 0",
        )
        self.assertRegex(
            self.css,
            r"\.education-list\s*\{[\s\S]*?gap:\s*14px",
        )
        self.assertRegex(
            self.css,
            r"\.education-item\s*\{[\s\S]*?gap:\s*32px"
            r"[\s\S]*?min-height:\s*64px",
        )
        self.assertRegex(
            self.css,
            r"\.content-section > :last-child\s*\{[\s\S]*?margin-bottom:\s*15px",
        )
        self.assertRegex(
            self.css,
            r"\.about-body\s*\{[\s\S]*?margin:\s*5px",
        )

    def test_academic_services_uses_compact_abbreviation_list(self):
        self.assertIn(
            '<i class="fa-solid fa-server" aria-hidden="true"></i> Academic Services',
            self.html,
        )
        self.assertNotIn("Professional Activities", self.html)
        self.assertIn(
            "<li><strong>Conference Reviewer:</strong> "
            "CVPR, ICCV, ECCV, NeurIPS, ICLR, ICML, ICRA, IROS</li>",
            self.html,
        )
        self.assertIn(
            "<li><strong>Journal Reviewer:</strong> "
            "IJCV, TPAMI, TNNLS, TCSVT, TMM, TMI, MIA</li>",
            self.html,
        )
        self.assertNotIn('class="service-group"', self.html)
        self.assertNotIn('class="service-list"', self.html)
        self.assertNotIn(".service-group", self.css)
        self.assertNotIn(".service-list", self.css)

    def test_typography_matches_reference_template(self):
        self.assertRegex(self.css, r"--body:\s*#111")
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertIn('<a href="#about"><b>About</b></a>', self.html)
        self.assertRegex(
            self.css,
            r"\.site-nav a\s*\{[\s\S]*?color:\s*#002336"
            r"[\s\S]*?font-weight:\s*400",
        )
        self.assertRegex(
            self.css,
            r"\.section-heading\s*\{[\s\S]*?color:\s*#111"
            r"[\s\S]*?font-size:\s*24px[\s\S]*?font-weight:\s*400",
        )
        self.assertRegex(
            self.css,
            r"\.section-heading i\s*\{[\s\S]*?color:\s*#111",
        )
        self.assertRegex(
            self.css,
            r"\.profile-title\s*\{[\s\S]*?font-size:\s*24px"
            r"[\s\S]*?font-weight:\s*200",
        )
        self.assertRegex(
            self.css,
            r"\.profile-email\s*\{[\s\S]*?font-size:\s*18px"
            r"[\s\S]*?font-weight:\s*200",
        )
        self.assertRegex(
            self.css,
            r"\.education-content h3\s*\{[\s\S]*?font-weight:\s*400",
        )
        self.assertRegex(
            self.css,
            r"\.simple-list strong\s*\{[\s\S]*?font-weight:\s*400",
        )
        self.assertRegex(
            self.css,
            r"\.publication-authors\s*\{[\s\S]*?color:\s*#4f5964",
        )
        self.assertRegex(
            self.css,
            r"\.publication-authors strong\s*\{[\s\S]*?color:\s*#872d22"
            r"[\s\S]*?font-weight:\s*600",
        )
        self.assertRegex(
            self.css,
            r"\.education-content\s*\{[\s\S]*?color:\s*#222",
        )
        education_heading_rule = re.search(
            r"\.education-content h3\s*\{(?P<body>[\s\S]*?)\}",
            self.css,
        )
        self.assertIsNotNone(education_heading_rule)
        self.assertNotIn("color", education_heading_rule.group("body"))
        self.assertRegex(
            self.css,
            r"\.publication-title\s*\{[\s\S]*?font-weight:\s*600",
        )
        for emphasized_label in ("<strong>Research Intern</strong>",):
            self.assertIn(emphasized_label, self.html)

    def test_honors_copy_and_golden_reviewer_award(self):
        self.assertIn('href="#awards"><b>Honors</b></a>', self.html)
        self.assertLess(
            self.html.index('id="awards"'),
            self.html.index('id="activities"'),
        )
        self.assertLess(
            self.html.index('href="#awards"'),
            self.html.index('href="#activities"'),
        )
        self.assertIn("Selected Honors", self.html)
        self.assertIn("<li>Golden Reviewer Award, ICML 2026</li>", self.html)
        self.assertIn(
            "<li>Postgraduate Studentship, CUHK, 2021–2026</li>",
            self.html,
        )
        self.assertIn(
            "<li>First Class Scholarship, 2019–2020</li>",
            self.html,
        )
        self.assertNotIn("Self-Reliance Scholarship", self.html)

    def test_honor_entries_are_unemphasized_bullets(self):
        for dropped in ('class="award-title"', 'class="dated-list"', "<time>"):
            self.assertNotIn(dropped, self.html)
        self.assertIn('<ul class="bullet-list">', self.html)
        self.assertRegex(
            self.css,
            r"\.bullet-list\s*\{[\s\S]*?margin:\s*0 0 15px 30px"
            r"[\s\S]*?padding:\s*0[\s\S]*?list-style:\s*disc",
        )

    def test_miscellaneous_section_lists_personal_interests(self):
        self.assertIn(
            '<a href="#miscellaneous"><b>Miscellaneous</b></a>',
            self.html,
        )
        self.assertIn(
            '<i class="fa-solid fa-puzzle-piece" aria-hidden="true"></i> '
            "Miscellaneous",
            self.html,
        )
        self.assertIn(
            "Curiosity and enthusiasm shape both my research and my life. "
            "I'm also passionate about basketball🏀, hiking⛰️, swimming🏊‍♂️, "
            "table tennis🏓, and badminton🏸.",
            self.html,
        )
        for removed_interest in ("jogging🏃‍♂️", "skiing🏂", "tennis🎾"):
            self.assertNotIn(removed_interest, self.html)
        self.assertLess(
            self.html.index('id="activities"'),
            self.html.index('id="miscellaneous"'),
        )

if __name__ == "__main__":
    unittest.main()
