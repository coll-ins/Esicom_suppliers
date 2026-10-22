#!/usr/bin/env python3
"""Dependency-free static production builder for Esicom Suppliers."""
from pathlib import Path
import json, os, shutil, re, sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ASSETS = ROOT / 'public'
NAVY = '#183c35'
PAGES = {
 '/': {'title':'Everything your office', 'highlight':'needs.', 'eyebrow':'A Nairobi supplier for the workday', 'intro':'Everyday stationery, printing supplies and branded merchandise. Tell us what you need; we’ll take it from there.', 'image':'/images/photography/meeting-room.webp', 'kind':'home'},
 '/office-supplies/': {'title':'The everyday essentials.', 'eyebrow':'OFFICE SUPPLIES', 'intro':'Pens, paper, notebooks and office supplies for the workday.', 'image':'/images/photography/stock-boxed-pens.webp', 'items':['Pens and writing materials','Notebooks, pads and diaries','Files and folders','Printing paper and desk essentials','Office stationery for teams and organisations'], 'kind':'detail'},
 '/computer-consumables/': {'title':'Keep work moving.', 'eyebrow':'COMPUTER CONSUMABLES', 'intro':'Toners, ink cartridges and computer essentials. Share your printer model and we’ll help you find the right fit.', 'image':'/images/photography/computer.webp', 'items':['Printer toners','Ink cartridges','Computer appliances and accessories','Consumable sourcing enquiries','Product model and specification checks before quotation'], 'kind':'detail'},
 '/bulk-printing/': {'title':'Let’s get your print job sorted.', 'eyebrow':'BULK PRINTING', 'intro':'Tell us what you’re printing, how many you need and when you need them.', 'image':'/images/photography/printing.webp', 'items':['Bulk printed business materials','Business documents and stationery','Quantity, size and finish discussions','Print-ready artwork coordination','Quotation based on your brief'], 'kind':'detail'},
 '/branding/': {'title':'Give your brand a useful life.', 'eyebrow':'CORPORATE BRANDING', 'intro':'Branded shirts, business cards, diaries and practical merchandise. Bring your logo and tell us what you have in mind.', 'image':'/images/photography/apparel.webp', 'items':['Branded shirts and apparel','Business cards','Branded diaries and stationery','Asset tags and identification','Custom corporate branding enquiries'], 'kind':'branding'},
 '/about/': {'title':'One local team for the workday.', 'eyebrow':'ABOUT ESICOM SUPPLIERS', 'intro':'We help Nairobi businesses source everyday office supplies, printing and branded merchandise.', 'image':'/images/photography/meeting-room.webp', 'items':['Office stationery and workplace essentials','Printing paper, files, notebooks and pens','Toners, cartridges and computer-related supplies','Bulk printing for business materials','Branded shirts, business cards, diaries and asset tags'], 'kind':'detail'},
 '/contact/': {'title':'What can we help you find?', 'eyebrow':'CONTACT · REQUEST A QUOTE', 'intro':'Send us your list, product photo or print brief. Our team in Nairobi will take it from there.', 'image':'/images/photography/workspace.webp', 'kind':'contact'},
 '/send-file/': {'title':'Send a file to Esicom', 'eyebrow':'FILE UPLOAD', 'intro':'Upload a document or image, convert it if needed, and send it to our team.', 'image':'', 'kind':'upload'},
 '/file-qr/': {'title':'Scan to send a file', 'eyebrow':'FILE UPLOAD QR', 'intro':'Print this QR code so customers can open the secure file upload page on their phones.', 'image':'', 'kind':'qr'},
 '/paper-filing/': {'title':'Paper, pens and the rest.', 'eyebrow':'PAPER & FILING', 'intro':'Reams of copy paper, boxed stationery, files and folders. Let us know what your office needs.', 'image':'/images/photography/stock-copy-paper.webp', 'items':['Copy paper and reams','Files and folders','Notebooks and writing pads','Document organisation supplies','Bulk supply enquiries for offices and teams'], 'kind':'detail'},
 '/business-cards/': {'title':'Business cards, made personal.', 'eyebrow':'BUSINESS CARDS', 'intro':'Tell us about the artwork, quantity and finish you have in mind.', 'image':'/images/photography/printing.webp', 'items':['Business card printing enquiries','Artwork and design file coordination','Quantity and finish discussions','Quotation based on specifications'], 'kind':'detail'},
 '/branded-apparel/': {'title':'Merchandise made yours.', 'eyebrow':'BRANDED APPAREL', 'intro':'Bring your logo and team requirements. We’ll discuss apparel and other branded items with you.', 'image':'/images/photography/apparel.webp', 'items':['Branded shirts','Team and event apparel enquiries','Logo artwork coordination','Quantity and sizing discussions','Quotation based on your brief'], 'kind':'detail'},
 '/diaries-asset-tags/': {'title':'Useful things, with your name on them.', 'eyebrow':'DIARIES & ASSET TAGS', 'intro':'Branded diaries, stationery and asset tags for your organisation.', 'image':'/images/photography/stationery.webp', 'items':['Branded diaries','Branded stationery','Asset tags','Organisation and identification materials','Bulk quotation enquiries'], 'kind':'detail'},
}

CSS = r'''@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--navy:#10243d;--blue:#183f67;--pale:#eaf1f8;--paper:#f5f8fc;--muted:#65768a;--line:#dbe4ed;--white:#fff;--shadow:0 22px 70px rgba(16,36,61,.12)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--navy);font-family:'DM Sans',sans-serif;line-height:1.6}a{color:inherit;text-decoration:none}img{max-width:100%;display:block}button,input,select,textarea{font:inherit}.wrap{width:min(1240px,calc(100% - 48px));margin-inline:auto}.topline{background:var(--navy);color:#d8e8f6;font-size:12px;padding:8px 0}.topline .wrap{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}.header{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.navrow{min-height:86px;display:flex;align-items:center;justify-content:space-between;gap:22px}.brand{display:flex;align-items:center;gap:11px;flex-shrink:0}.brand-mark{display:grid;place-items:center;width:43px;height:43px;border-radius:13px;background:var(--navy);color:white;font:800 22px Manrope,sans-serif}.brand-name{font:800 15px Manrope,sans-serif;letter-spacing:.16em;line-height:1.2}.brand-sub{display:block;color:var(--muted);font:700 9px 'DM Sans',sans-serif;letter-spacing:.25em;text-transform:uppercase;margin-top:4px}.navlinks{display:flex;align-items:center;gap:21px;font-size:12px;font-weight:700}.navlinks a{padding:8px 0;border-bottom:2px solid transparent}.navlinks a:hover,.navlinks a[aria-current=page]{border-color:var(--blue)}.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;border:1px solid transparent;border-radius:999px;padding:14px 21px;font-size:13px;font-weight:800;transition:transform .2s,background .2s;cursor:pointer}.btn:hover{transform:translateY(-2px)}.btn-primary{background:var(--navy);color:white}.btn-primary:hover{background:var(--blue)}.btn-light{background:white;border-color:var(--line)}.btn-blue{background:var(--blue);color:white}.nav-actions{display:flex;gap:10px;align-items:center}.menu-btn{display:none;border:1px solid var(--line);background:white;border-radius:12px;width:44px;height:44px;font-size:20px}.hero{padding:66px 0 74px;overflow:hidden;background:linear-gradient(105deg,var(--paper) 0%,var(--paper) 48%,#e4edf6 48%,#e4edf6 100%)}.hero-grid{display:grid;grid-template-columns:.95fr 1.05fr;gap:58px;align-items:center}.eyebrow{display:flex;align-items:center;gap:10px;color:var(--blue);font-size:10px;font-weight:800;letter-spacing:.2em;text-transform:uppercase}.eyebrow:before{content:'';width:27px;height:2px;background:currentColor}.hero h1{font:800 clamp(46px,6.8vw,90px)/.96 Manrope,sans-serif;letter-spacing:-.075em;margin:24px 0}.hero h1 span{color:var(--blue)}.lead{max-width:510px;font-size:17px;line-height:1.8;color:#52677e}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.hero-visual{position:relative;min-width:0}.hero-visual img{width:100%;height:470px;object-fit:cover;border-radius:30px;box-shadow:var(--shadow)}.floating-note{position:absolute;left:-24px;top:30px;background:#fff;border:1px solid #fff;border-radius:15px;padding:15px 18px;box-shadow:var(--shadow);font-size:12px;font-weight:800}.visual-caption{position:absolute;bottom:18px;left:18px;right:18px;background:rgba(16,36,61,.84);color:#fff;border-radius:16px;padding:17px 20px;font:700 19px Manrope,sans-serif;backdrop-filter:blur(8px)}.strip{background:white;border-block:1px solid var(--line)}.strip-grid{display:grid;grid-template-columns:repeat(4,1fr)}.strip-item{padding:24px 18px;border-right:1px solid var(--line)}.strip-item:last-child{border:0}.strip-item b{display:block;font:800 23px Manrope,sans-serif;color:var(--blue)}.strip-item span{display:block;color:var(--muted);font-size:12px;margin-top:3px}.section{padding:82px 0}.section.white{background:#fff}.section.dark{background:var(--navy);color:white}.section-head{display:flex;align-items:end;justify-content:space-between;gap:30px;margin-bottom:32px}.section h2,.section-head h2{font:800 clamp(30px,4.2vw,52px)/1.08 Manrope,sans-serif;letter-spacing:-.055em;margin:12px 0}.section-head p{max-width:420px;color:var(--muted);margin:0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{border:1px solid var(--line);background:white;border-radius:23px;overflow:hidden;transition:transform .25s,box-shadow .25s}.card:hover{transform:translateY(-5px);box-shadow:var(--shadow)}.card img{width:100%;height:250px;object-fit:cover;background:var(--pale)}.card-body{padding:22px}.card-body h3{font:800 20px Manrope,sans-serif;margin:0 0 8px}.card-body p{color:var(--muted);font-size:14px;line-height:1.7;margin:0 0 16px}.link{display:inline-flex;align-items:center;gap:8px;color:var(--blue);font-size:13px;font-weight:800}.link:after{content:'↗';font-size:17px}.service-panel{display:grid;grid-template-columns:1fr 1fr;gap:24px}.service-feature{position:relative;min-height:360px;border-radius:25px;overflow:hidden;background:var(--navy)}.service-feature img{position:absolute;width:100%;height:100%;object-fit:cover;opacity:.76}.service-feature:after{content:'';position:absolute;inset:0;background:linear-gradient(0deg,rgba(16,36,61,.95),transparent 75%)}.service-feature div{position:absolute;z-index:1;left:25px;right:25px;bottom:24px;color:white}.service-feature h3{font:800 27px Manrope,sans-serif;margin:0 0 8px}.service-feature p{max-width:400px;color:#e0e9f2;margin:0 0 15px;font-size:14px}.cta-band{background:#dce8f4;border-radius:28px;padding:36px;display:flex;align-items:center;justify-content:space-between;gap:22px}.cta-band h2{font:800 clamp(27px,3.5vw,42px)/1.12 Manrope,sans-serif;margin:10px 0}.page-hero{padding:58px 0 55px;background:linear-gradient(115deg,#f5f8fc 0%,#f5f8fc 55%,#e4edf6 55%)}.page-hero-grid{display:grid;grid-template-columns:1fr .8fr;align-items:center;gap:52px}.page-hero h1{font:800 clamp(38px,5vw,66px)/1.04 Manrope,sans-serif;letter-spacing:-.06em;margin:17px 0}.page-hero p{font-size:16px;color:#53677d;max-width:620px;line-height:1.85}.page-hero img{height:300px;width:100%;object-fit:cover;border-radius:24px;box-shadow:var(--shadow)}.detail-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:45px;align-items:start}.check-list{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.check-item{padding:17px;border:1px solid var(--line);border-radius:15px;background:white;font-size:13px;font-weight:700;display:flex;gap:11px;align-items:flex-start}.check-item:before{content:'✓';display:grid;place-items:center;flex-shrink:0;width:24px;height:24px;background:var(--pale);color:var(--blue);border-radius:50%;font-weight:900}.form-layout{display:grid;grid-template-columns:.75fr 1.25fr;gap:44px}.contact-list{display:grid;gap:18px;margin-top:28px}.contact-item{display:flex;align-items:center;gap:14px}.contact-icon{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;background:var(--pale);font-size:19px}.contact-item small{display:block;color:var(--muted);font-size:11px}.contact-item b{font-size:14px;overflow-wrap:anywhere}.quote-form{background:white;border:1px solid var(--line);border-radius:24px;padding:28px;box-shadow:var(--shadow)}.quote-form h2{font:800 26px Manrope,sans-serif;margin:0 0 6px}.quote-form>p{color:var(--muted);font-size:13px;margin:0 0 22px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.field{display:grid;gap:7px;font-size:12px;font-weight:800}.field.full{grid-column:1/-1}.field input,.field select,.field textarea{width:100%;border:1px solid #ccd8e5;border-radius:11px;padding:12px 13px;background:#fff;color:var(--navy);outline:none}.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px #183f671a}.field textarea{resize:vertical;min-height:110px}.form-status{margin-top:15px;padding:13px 15px;background:var(--pale);border-radius:12px;font-size:13px;color:var(--navy)}.footer{background:var(--navy);color:white;padding:52px 0 20px}.footer-grid{display:grid;grid-template-columns:1.2fr .8fr .8fr 1fr;gap:30px;padding-bottom:35px;border-bottom:1px solid #ffffff24}.footer h3{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#c7d9eb}.footer a,.footer p{font-size:13px;color:#d5dfeb}.footer-links{display:grid;gap:10px}.footer-bottom{display:flex;justify-content:space-between;gap:12px;padding-top:17px;color:#aebdce;font-size:11px}.whatsapp{position:fixed;z-index:30;bottom:20px;right:20px;background:#183f67;color:#fff;border-radius:999px;padding:13px 18px;box-shadow:var(--shadow);font-size:13px;font-weight:800}.mockup-label{display:inline-block;border-radius:999px;background:var(--pale);padding:7px 12px;color:var(--blue);font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.catalogue-callout{display:flex;align-items:center;justify-content:space-between;gap:20px;background:white;border:1px solid var(--line);border-radius:18px;padding:20px;margin-top:25px}.catalogue-callout strong{font:800 17px Manrope,sans-serif}.catalogue-callout p{margin:5px 0 0;font-size:13px;color:var(--muted)}.mobile-nav{display:none}
@media(max-width:1100px){.navlinks{gap:12px;font-size:11px}.nav-actions .catalogue-btn{display:none}.nav-actions .quote-btn{padding:12px 15px}.hero-grid{gap:30px}.hero-visual img{height:420px}}
@media(max-width:900px){.wrap{width:min(100% - 36px,700px)}.navrow{min-height:74px}.navlinks{display:none}.nav-actions .quote-btn{display:none}.menu-btn{display:block}.mobile-nav.open{display:grid;padding:0 18px 16px;gap:4px}.mobile-nav a{padding:11px 12px;border-radius:10px;font-size:13px;font-weight:700}.mobile-nav a:hover{background:var(--pale)}.hero{padding:42px 0 54px;background:linear-gradient(160deg,var(--paper) 0%,var(--paper) 60%,#e4edf6 60%)}.hero-grid,.page-hero-grid,.detail-grid,.form-layout{grid-template-columns:1fr}.hero-grid{gap:34px}.hero-visual img{height:360px}.floating-note{left:12px;top:12px}.strip-grid{grid-template-columns:repeat(2,1fr)}.strip-item:nth-child(2){border-right:0}.strip-item:nth-child(-n+2){border-bottom:1px solid var(--line)}.section{padding:60px 0}.section-head{align-items:start;flex-direction:column}.cards{grid-template-columns:repeat(2,1fr)}.service-panel{grid-template-columns:1fr 1fr}.page-hero{padding:42px 0}.page-hero-grid{gap:24px}.page-hero img{height:280px}.footer-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.wrap{width:calc(100% - 30px)}.topline .wrap{justify-content:center;text-align:center}.hero h1{font-size:clamp(46px,14vw,72px)}.hero-visual img{height:300px;border-radius:20px}.visual-caption{font-size:16px}.cards,.service-panel,.check-list,.form-grid{grid-template-columns:1fr}.card img{height:220px}.service-feature{min-height:320px}.cta-band{align-items:flex-start;flex-direction:column;padding:25px}.page-hero h1{font-size:39px}.page-hero img{height:230px}.quote-form{padding:19px}.field.full{grid-column:auto}.footer-grid{grid-template-columns:1fr;gap:25px}.footer-bottom{flex-direction:column}.whatsapp{right:12px;bottom:12px;padding:12px 14px}.catalogue-callout{align-items:flex-start;flex-direction:column}}
html{scroll-padding-top:100px}
main[id]{scroll-margin-top:100px}
:focus-visible{outline:3px solid #3975a8;outline-offset:4px}
.skip-link{position:fixed;z-index:100;top:12px;left:12px;transform:translateY(-160%);padding:12px 16px;border-radius:10px;background:#fff;color:var(--navy);font-weight:800;box-shadow:var(--shadow)}
.skip-link:focus{transform:translateY(0)}
.mobile-nav{max-height:calc(100vh - 74px);overflow-y:auto}
.mobile-nav a[aria-current=page]{background:var(--pale);color:var(--blue)}
.btn:focus-visible,.menu-btn:focus-visible,.whatsapp:focus-visible{outline-offset:3px}
@media(max-width:600px){.hero{padding-top:34px}.hero-grid{gap:27px}.strip-item{padding:19px 14px}.strip-item b{font-size:20px}.section{padding:50px 0}.page-hero{padding:34px 0}.actions .btn{flex:1 1 auto}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}
:root{--navy:#183c35;--blue:#47735f;--pale:#e8eee6;--paper:#f6f4ee;--muted:#64736b;--line:#dce3da;--white:#fff;--gold:#b8894f;--shadow:0 26px 72px rgba(24,60,53,.14)}
body{background:var(--paper);color:#203b34}
.topline{background:#14332d;color:#e8eee6}
.header{background:rgba(250,249,245,.94);box-shadow:0 8px 32px rgba(24,60,53,.055)}
.brand-mark{background:linear-gradient(145deg,#214b40,#102c26);box-shadow:inset 0 1px 0 #ffffff30,0 8px 20px #17392c25}
.navlinks a:hover,.navlinks a[aria-current=page]{border-color:var(--gold)}
.btn{border-radius:10px;padding:14px 20px;box-shadow:0 7px 18px rgba(24,60,53,.08)}
.btn-primary{background:linear-gradient(135deg,#245644,#153c32);box-shadow:0 9px 20px rgba(24,60,53,.2),inset 0 1px 0 #ffffff25}
.btn-primary:hover{background:linear-gradient(135deg,#326b54,#1b493c);box-shadow:0 13px 26px rgba(24,60,53,.24)}
.btn-light{background:#fffefa;border-color:#d8dfd5}
.menu-btn{border-radius:10px}
.hero{position:relative;isolation:isolate;padding:84px 0 86px;background:radial-gradient(ellipse at 87% 37%,rgba(222,232,218,.95),transparent 39%),linear-gradient(108deg,#f7f5ef 0%,#f7f5ef 52%,#edf0e8 52%,#edf0e8 100%)}
.hero:before{content:"";position:absolute;z-index:-1;width:360px;height:360px;right:-155px;top:-145px;border:1px solid rgba(184,137,79,.24);border-radius:50%;box-shadow:0 0 0 30px rgba(255,255,255,.18),0 0 0 60px rgba(255,255,255,.12)}
.hero-grid{grid-template-columns:1fr 1.02fr;gap:clamp(38px,6vw,86px)}
.eyebrow{color:#547760;letter-spacing:.18em}
.eyebrow:before{width:30px;height:2px;color:var(--gold);background:var(--gold)}
.hero h1{font-size:clamp(49px,6.2vw,82px);letter-spacing:-.07em;line-height:.99;margin:25px 0 21px}
.hero h1 span{color:#4e775f}
.lead{max-width:490px;color:#5e6f66;font-size:17px;line-height:1.8}
.hero .actions{margin-top:30px}
.hero-visual{perspective:1400px;transform-style:preserve-3d}
.hero-visual:before{content:"";position:absolute;z-index:-1;inset:17px -17px -15px 17px;border:1px solid rgba(184,137,79,.5);border-radius:30px;transform:rotate(2.5deg) translateZ(-28px)}
.hero-visual img{height:500px;border-radius:25px;transform:rotateY(-4deg) rotateX(1.5deg) translateZ(10px);box-shadow:0 38px 80px rgba(21,49,41,.23),0 12px 26px rgba(21,49,41,.14);transition:transform .55s cubic-bezier(.2,.7,.2,1),box-shadow .55s}
.hero-visual:hover img{transform:rotateY(-1deg) rotateX(0) translateY(-5px) translateZ(16px);box-shadow:0 48px 95px rgba(21,49,41,.27),0 14px 30px rgba(21,49,41,.16)}
.floating-note{left:-30px;top:28px;border:1px solid #ffffffcf;border-radius:12px;color:#244438;box-shadow:0 16px 35px rgba(21,49,41,.16);letter-spacing:.035em}
.visual-caption{background:linear-gradient(105deg,rgba(19,48,41,.93),rgba(32,71,57,.8));border:1px solid #ffffff2c;border-radius:13px;box-shadow:0 8px 25px #09251f40}
.mockup-label{background:#e7eee5;color:#426650;letter-spacing:.1em}
.strip{background:#fffefa;border-color:var(--line)}
.strip-item{position:relative;padding-block:25px}
.strip-item b{color:#b8894f;font-size:21px}
.strip-item span{color:#52665d;font-size:12px;font-weight:700;letter-spacing:.015em}
.section{padding:88px 0}
.section h2,.section-head h2{letter-spacing:-.045em}
.section-head p{color:#66746c;line-height:1.8}
.section.dark{background:radial-gradient(ellipse at 87% 15%,#2a5749 0%,transparent 40%),#173a32}
.section.dark .eyebrow{color:#d6c09a}
.section.dark .eyebrow:before{background:#c39a63}
.section.dark .section-head p{color:#d1ded4}
.card{border-color:#e5e6dd;border-radius:16px;background:#fffefa;box-shadow:0 8px 25px rgba(29,55,46,.045);transition:transform .35s cubic-bezier(.2,.7,.2,1),box-shadow .35s,border-color .35s}
.card:hover{transform:translateY(-8px) rotateX(1deg);border-color:#c8d4c9;box-shadow:0 24px 48px rgba(29,55,46,.14)}
.card img{height:260px;object-fit:cover;transition:transform .55s cubic-bezier(.2,.7,.2,1)}
.card:hover img{transform:scale(1.035)}
.card-body{padding:23px}
.card-body h3{color:#213e34}
.card-body p{color:#65736b}
.link{color:#47735f}
.link:after{color:var(--gold)}
.service-feature{min-height:385px;border-radius:18px;box-shadow:0 20px 45px rgba(3,19,15,.25);transition:transform .4s,box-shadow .4s}
.service-feature:hover{transform:translateY(-7px) rotateX(1deg);box-shadow:0 30px 60px rgba(3,19,15,.34)}
.service-feature img{transition:transform .6s}
.service-feature:hover img{transform:scale(1.04)}
.service-feature:after{background:linear-gradient(0deg,rgba(13,38,31,.97),rgba(13,38,31,.03) 82%)}
.cta-band{position:relative;overflow:hidden;background:linear-gradient(120deg,#e6ece2,#f2ebdd);border:1px solid #e2e4d9;border-radius:18px;box-shadow:0 18px 45px rgba(34,66,54,.08)}
.cta-band:after{content:"";position:absolute;width:210px;height:210px;right:13%;top:-150px;border:1px solid rgba(184,137,79,.4);border-radius:50%;box-shadow:0 0 0 20px rgba(255,255,255,.13),0 0 0 40px rgba(255,255,255,.1);pointer-events:none}
.page-hero{background:radial-gradient(ellipse at 90% 35%,rgba(218,229,215,.95),transparent 36%),linear-gradient(110deg,#f7f5ef 0%,#f7f5ef 56%,#edf0e8 56%,#edf0e8 100%)}
.page-hero h1{color:#1d3d33;letter-spacing:-.055em}
.page-hero p{color:#5e6f66;line-height:1.8}
.page-hero img{border-radius:18px;box-shadow:0 28px 65px rgba(21,49,41,.2),0 8px 20px rgba(21,49,41,.1);transform:rotateY(-3deg);transition:transform .45s}
.page-hero img:hover{transform:rotateY(0) translateY(-4px)}
.detail-grid{gap:55px}
.check-item{background:#fffefa;border-color:#e0e5dd;border-radius:13px;color:#29463b}
.check-item:before{background:#e7eee5;color:#46705a}
.quote-form{background:#fffefa;border-color:#e0e5dd;border-radius:18px;box-shadow:0 22px 55px rgba(26,55,45,.1)}
.field input,.field select,.field textarea{border-color:#d6ded5;border-radius:9px}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#5b8067;box-shadow:0 0 0 3px #47735f20}
.form-status{background:#e7eee5;color:#244438}
.footer{background:radial-gradient(ellipse at 78% 0%,#285344 0%,transparent 39%),#15362f}
.footer .brand-mark{background:#f7f4eb!important;color:#183c35!important}
.footer h3{color:#dac8a7}
.whatsapp{background:#285d48;border:1px solid #ffffff22;border-radius:10px;box-shadow:0 10px 26px rgba(13,38,30,.24)}
.whatsapp:hover{background:#347255;transform:translateY(-3px)}
.catalogue-callout{background:#fffefa;border-color:#e1e5dc;border-radius:14px}
.photo-credit{display:block;margin:0 0 12px;color:#788279;font-size:10px;line-height:1.6}
.photo-credit a{color:inherit;text-decoration:underline;text-underline-offset:2px}
.catalog-item-note{margin-top:16px;color:var(--muted);font-size:12px}
@media(max-width:900px){.hero{background:radial-gradient(ellipse at 88% 72%,#e1e9df,transparent 40%),#f7f5ef}.hero:before{right:-230px}.hero-visual img{height:390px}.hero-visual:before{inset:13px -10px -12px 12px}.page-hero{background:radial-gradient(ellipse at 90% 75%,#e1e9df,transparent 38%),#f7f5ef}.page-hero img{transform:none}.page-hero img:hover{transform:translateY(-3px)}}
@media(max-width:900px){.hero-grid{grid-template-columns:1fr}.hero-visual{max-width:680px;width:100%;margin-inline:auto}.hero-visual img{transform:none}}
@media(max-width:600px){.hero{padding-top:39px;padding-bottom:48px}.hero h1{font-size:clamp(45px,12.5vw,67px);line-height:1.02}.hero-visual img{height:290px;border-radius:17px;transform:none}.hero-visual:hover img{transform:translateY(-3px)}.hero-visual:before{inset:10px -7px -10px 8px;border-radius:19px}.floating-note{left:10px;top:10px;padding:11px 13px;font-size:10px}.visual-caption{left:12px;right:12px;bottom:12px;padding:13px 15px}.section{padding:55px 0}.card img{height:225px}.service-feature{border-radius:15px}.cta-band{border-radius:15px}.page-hero img{border-radius:15px}.strip-item{padding:18px 12px}.strip-item b{font-size:18px}.actions .btn{flex:1 1 auto}}
.service-panel.premium-services{grid-template-columns:repeat(3,minmax(0,1fr))}
.service-panel.premium-services .service-feature{min-height:340px}
@media(max-width:900px){.service-panel.premium-services{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.service-panel.premium-services{grid-template-columns:1fr}.service-panel.premium-services .service-feature{min-height:300px}}
.upload-shell{padding:64px 0 80px;background:linear-gradient(145deg,#f7f5ef,#e9eee7)}
.upload-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(290px,.75fr);gap:32px;align-items:start}
.upload-card,.qr-card{background:#fffefa;border:1px solid #e0e5dd;border-radius:20px;padding:clamp(22px,4vw,42px);box-shadow:0 20px 55px rgba(26,55,45,.08)}
.upload-card h1,.qr-card h1{font:800 clamp(35px,5vw,54px)/1.05 Manrope,sans-serif;letter-spacing:-.06em;margin:0 0 14px}
.upload-card>p,.qr-card>p{color:var(--muted)}
.upload-card .field{margin-top:17px}
.upload-card [hidden]{display:none!important}
.upload-card input[type=file]{padding:13px;background:#fff}
.upload-note{font-size:12px;color:var(--muted)}
.upload-result{margin-top:18px;padding:16px;background:#e7eee5;border-radius:12px}
.upload-result[hidden]{display:none}
.qr-shell{padding:64px 0 80px}
.qr-card{max-width:760px;margin-inline:auto;text-align:center}
.qr-image{width:min(330px,80vw);aspect-ratio:1;margin:26px auto;object-fit:contain;padding:12px;border:1px solid var(--line);border-radius:12px}
.qr-actions{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}
.qr-instructions{max-width:540px;margin:0 auto 20px;color:var(--muted)}
@media(max-width:760px){.upload-shell,.qr-shell{padding:36px 0 55px}.upload-grid{grid-template-columns:1fr}}
@media print{.topline,.header,.footer,.whatsapp,.qr-actions,.skip-link{display:none!important}body,.qr-shell{background:#fff!important}.wrap{width:100%}.qr-card{border:0;box-shadow:none;padding:15mm}.qr-image{width:85mm;margin:12mm auto}.qr-card h1{font-size:28pt}}

/* A darker, photo-led identity inspired by the reference while keeping Esicom's own palette. */
.header{background:rgba(20,51,45,.97);border-bottom-color:#ffffff1c;box-shadow:0 12px 35px rgba(13,38,31,.18)}
.brand-name{color:#fff}
.brand-sub{color:#c5d7ca}
.brand-mark{background:#f7f5ef;color:#183c35;box-shadow:none}
.navlinks a{color:#edf4ed}
.navlinks a:hover,.navlinks a[aria-current=page]{border-color:#69b875;color:#fff}
.header .btn-light{background:transparent;border-color:#ffffff55;color:#fff;box-shadow:none}
.header .btn-primary{background:#2f9b55;color:#fff;box-shadow:0 8px 22px rgba(24,111,58,.28)}
.header .btn-primary:hover{background:#38ad63}
.menu-btn{background:transparent;border-color:#ffffff55;color:#fff}
.mobile-nav{background:#14332d;border-top-color:#ffffff20}
.mobile-nav a{color:#edf4ed}
.mobile-nav a:hover,.mobile-nav a[aria-current=page]{background:#ffffff12;color:#fff}
.hero{padding:88px 0 92px;background:radial-gradient(ellipse at 90% 32%,rgba(218,231,216,.88),transparent 42%),linear-gradient(112deg,#f8f7f2 0%,#f8f7f2 50%,#eaf0e8 50%,#eaf0e8 100%)}
.hero h1{max-width:650px;font-size:clamp(52px,6.4vw,88px);line-height:.98}
.hero h1 span{color:#347d4a}
.hero-visual img{height:520px;border-radius:20px;transform:none;box-shadow:0 34px 72px rgba(21,49,41,.22)}
.hero-visual:hover img{transform:translateY(-5px);box-shadow:0 42px 85px rgba(21,49,41,.27)}
.hero-visual:before{border-radius:22px}
.visual-caption{background:linear-gradient(105deg,rgba(18,48,39,.94),rgba(34,80,52,.82))}
.btn-primary{background:#267a46}
.btn-primary:hover{background:#338b52}
.section-head h2{color:#1d3d33}
.section.dark .section-head h2{color:#fff}
.service-feature{min-height:390px}
.cta-band{background:linear-gradient(120deg,#e3ebdf,#f0e8d8);border-color:#dce3d8}
.footer{background:radial-gradient(ellipse at 78% 0%,#285344 0%,transparent 39%),#14332d}
.whatsapp{background:#218c4c}
.whatsapp:hover{background:#2ba45a}
@media(max-width:900px){
  .hero{padding:62px 0 66px;background:radial-gradient(ellipse at 88% 72%,#e1e9df,transparent 40%),#f7f5ef}
  .hero-visual img{height:420px}
}
@media(max-width:600px){
  .hero{padding:40px 0 50px}
  .hero h1{font-size:clamp(46px,12vw,68px)}
  .hero-visual img{height:290px}
}
.hero-visual{min-width:0}
.hero-carousel{position:relative;overflow:hidden;border-radius:22px;background:#173a32;box-shadow:0 34px 72px rgba(21,49,41,.22)}
.hero-slide-link{display:block;position:relative}
.hero-carousel img{height:520px;width:100%;object-fit:cover;opacity:1;transition:opacity .35s ease,transform .8s cubic-bezier(.2,.7,.2,1)}
.hero-carousel img.is-changing{opacity:.35;transform:scale(1.025)}
.hero-slide-link:after{content:"";position:absolute;inset:30% 0 0;background:linear-gradient(0deg,rgba(13,38,31,.78),transparent);pointer-events:none}
.hero-carousel .visual-caption{position:absolute;z-index:1;left:22px;right:22px;bottom:20px;display:flex;align-items:end;justify-content:space-between;gap:18px;background:transparent;border:0;box-shadow:none;padding:0}
.hero-caption-copy{display:grid;gap:4px}
.hero-caption-copy small{font-size:10px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:#d8c49f}
.hero-caption-copy strong{font:800 clamp(18px,2.2vw,25px)/1.15 Manrope,sans-serif;color:#fff}
.hero-slide-more{flex:0 0 auto;color:#fff;font-size:12px;font-weight:800}
.hero-carousel-controls{position:absolute;z-index:2;top:18px;right:18px;display:flex;align-items:center;gap:7px;padding:7px;border:1px solid #ffffff42;border-radius:999px;background:rgba(19,48,41,.7);backdrop-filter:blur(12px)}
.hero-carousel-controls button{display:grid;place-items:center;min-width:32px;height:32px;padding:0 9px;border:0;border-radius:999px;background:transparent;color:#fff;font:700 13px 'DM Sans',sans-serif;cursor:pointer}
.hero-carousel-controls button:hover,.hero-carousel-controls button:focus-visible{background:#ffffff24;outline:none}
.hero-carousel-controls [data-hero-dots]{display:flex;align-items:center;gap:5px}
.hero-carousel-controls [data-hero-dots] button{min-width:10px;width:10px;height:10px;padding:0;background:#ffffff75}
.hero-carousel-controls [data-hero-dots] button[aria-current=true]{width:24px;background:#d8c49f}
.hero-carousel .floating-note{z-index:2;top:20px;left:20px;border-radius:999px;padding:11px 15px;background:#fffefa;color:#244438}
.hero-carousel:before{display:none}
@media(max-width:900px){.hero-carousel img{height:420px}}
@media(max-width:600px){
 .hero-carousel{border-radius:16px}
 .hero-carousel img{height:300px}
 .hero-carousel .floating-note{top:13px;left:12px;padding:9px 12px}
 .hero-carousel-controls{top:12px;right:12px;gap:3px;padding:5px}
 .hero-carousel-controls button{min-width:28px;height:28px}
 .hero-carousel .visual-caption{left:14px;right:14px;bottom:14px}
 .hero-caption-copy strong{font-size:18px}
}
body.visual-editor-mode img,
body.visual-editor-mode h1,
body.visual-editor-mode h2,
body.visual-editor-mode h3,
body.visual-editor-mode p,
body.visual-editor-mode a,
body.visual-editor-mode button,
body.visual-editor-mode span,
body.visual-editor-mode small,
body.visual-editor-mode li,
body.visual-editor-mode .eyebrow,
body.visual-editor-mode .mockup-label{cursor:crosshair!important}
body.visual-editor-mode img:hover,
body.visual-editor-mode h1:hover,
body.visual-editor-mode h2:hover,
body.visual-editor-mode h3:hover,
body.visual-editor-mode p:hover,
body.visual-editor-mode a:hover,
body.visual-editor-mode button:hover,
body.visual-editor-mode span:hover,
body.visual-editor-mode small:hover,
body.visual-editor-mode li:hover,
body.visual-editor-mode .eyebrow:hover,
body.visual-editor-mode .mockup-label:hover,
body.visual-editor-mode .visual-editor-selected{outline:3px solid #b8894f!important;outline-offset:3px}
.cards[data-featured-products] .card img{height:300px}
.cards[data-featured-products] .card{border-radius:18px}
.editable-section{background:#fffefa}
.editable-section-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:36px;align-items:center}
.editable-section-card>img{width:100%;max-height:440px;object-fit:cover;border-radius:18px}
.editable-section-copy h2{font:800 clamp(29px,4vw,45px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:0 0 14px;color:#1d3d33}
.editable-section-copy p{color:var(--muted);line-height:1.85;white-space:pre-line;margin:0 0 20px}
@media(max-width:700px){.editable-section-card{grid-template-columns:1fr;gap:22px}}
@media(prefers-reduced-motion:reduce){.hero-carousel img{transition:none}}
'''

JS = r'''(()=>{
const menu=document.querySelector('[data-menu-button]');
const nav=document.querySelector('[data-mobile-nav]');
if(menu&&nav){
  const setMenuOpen=open=>{
    nav.classList.toggle('open',open);
    menu.setAttribute('aria-expanded',String(open));
    menu.setAttribute('aria-label',open?'Close navigation':'Open navigation');
    menu.textContent=open?'×':'☰';
  };
  menu.addEventListener('click',()=>setMenuOpen(!nav.classList.contains('open')));
  nav.addEventListener('click',event=>{
    if(event.target.closest('a'))setMenuOpen(false);
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&nav.classList.contains('open')){
      setMenuOpen(false);
      menu.focus();
    }
  });
}
const main=document.querySelector('main[data-content-page]');
const pageKey=main?.dataset.contentPage;
const localApiBase=['localhost','127.0.0.1'].includes(location.hostname)&&['4173','4174','5173'].includes(location.port)?'http://127.0.0.1:8000':'';
const apiBase=(window.ESICOM_API_BASE_URL||localApiBase).replace(/\/$/,'');
const imageUrl=path=>{
  if(/^(?:https?:|blob:|data:)/i.test(path))return path;
  const base=apiBase&&path.startsWith('/media/')?apiBase:location.origin;
  return new URL(path,base).href;
};
let photoOverrides={};
const siteImage=path=>{
  if(/^https?:\/\//i.test(path))return path;
  return imageUrl(photoOverrides[path]||path);
};
const visualEditorMode=new URLSearchParams(location.search).get('editor')==='1'&&window.parent!==window;
const editorParentOrigin=visualEditorMode?new URLSearchParams(location.search).get('editor_origin'):'';
const visualOriginals=new Map();
const editorSelector=element=>{
  const root=element.closest('main[data-content-page],header,footer,.topline');
  if(!root)return '';
  const rootSelector=root.matches('main[data-content-page]')
    ?'main[data-content-page="'+pageKey+'"]'
    :root.matches('.topline')?'.topline':root.localName;
  const marker=element.closest('[data-editor-key]');
  const stableMarker=marker&&root.contains(marker)?marker:null;
  const parts=[];
  let current=element;
  const stopAt=stableMarker||root;
  while(current&&current!==stopAt){
    const siblings=[...current.parentElement.children].filter(sibling=>sibling.tagName===current.tagName);
    parts.unshift(current.localName+':nth-of-type('+(siblings.indexOf(current)+1)+')');
    current=current.parentElement;
  }
  if(stableMarker){
    const markerSelector='[data-editor-key="'+stableMarker.dataset.editorKey+'"]';
    return rootSelector+' '+markerSelector+(parts.length?' > '+parts.join(' > '):'');
  }
  return current===root?rootSelector+' > '+parts.join(' > '):'';
};
const directText=element=>[...element.childNodes]
  .filter(node=>node.nodeType===Node.TEXT_NODE)
  .map(node=>node.textContent)
  .join('')
  .trim();
const rememberOriginal=target=>{
  const selector=editorSelector(target);
  if(selector&&!visualOriginals.has(selector)){
    visualOriginals.set(selector,{
      textNodes:[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent),
      image:target instanceof HTMLImageElement?target.getAttribute('src'):'',
      fontFamily:target.style.fontFamily,
      fontSize:target.style.fontSize,
      color:target.style.color,
      display:target.style.display,
    });
  }
  return visualOriginals.get(selector);
};
const setDirectText=(target,value)=>{
  const textNodes=[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE);
  if(textNodes.length){
    textNodes[0].textContent=value;
    textNodes.slice(1).forEach(node=>node.remove());
  }else target.insertBefore(document.createTextNode(value),target.firstChild);
};
const applyVisualEdits=edits=>{
  for(const edit of edits){
    if(edit.page!==pageKey&&edit.page!=='global')continue;
    const target=document.querySelector(edit.selector);
    if(!target)continue;
    rememberOriginal(target);
    if(edit.text!==null)setDirectText(target,edit.text);
    if(edit.image&&target instanceof HTMLImageElement)target.src=imageUrl(edit.image);
    if(edit.font_family)target.style.fontFamily='"'+edit.font_family+'"';
    if(edit.font_size)target.style.fontSize=edit.font_size+'px';
    if(edit.text_color)target.style.color=edit.text_color;
    if(edit.hidden)target.style.display='none';
  }
};
if(visualEditorMode){
  document.body.classList.add('visual-editor-mode');
  window.addEventListener('message',event=>{
    if(event.origin!==editorParentOrigin||event.source!==parent||event.data?.type!=='esicom-visual-editor-preview')return;
    const edit=event.data.edit;
    const target=document.querySelector(edit.selector);
    if(!target)return;
    const original=rememberOriginal(target);
    if(edit.text===null){
      const textNodes=[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE);
      textNodes.forEach(node=>node.remove());
      original.textNodes.forEach(text=>target.insertBefore(document.createTextNode(text),target.firstChild));
    }else setDirectText(target,edit.text);
    if(target instanceof HTMLImageElement){
      if(edit.image!==null)target.src=edit.image?imageUrl(edit.image):imageUrl(original.image);
    }
    target.style.fontFamily=edit.font_family?'"'+edit.font_family+'"':original.fontFamily;
    target.style.fontSize=edit.font_size?edit.font_size+'px':original.fontSize;
    target.style.color=edit.text_color||original.color;
    target.style.display=edit.hidden?'none':original.display;
  });
  document.addEventListener('click',event=>{
    const target=event.target.closest('img,h1,h2,h3,p,a,button,span,small,strong,b,li,.eyebrow,.mockup-label');
    if(!target||!target.closest('main[data-content-page],header,footer,.topline'))return;
    event.preventDefault();
    event.stopImmediatePropagation();
    document.querySelector('.visual-editor-selected')?.classList.remove('visual-editor-selected');
    target.classList.add('visual-editor-selected');
    if(!editorParentOrigin)return;
    parent.postMessage({
      type:'esicom-visual-editor-select',
      page:pageKey,
      selector:editorSelector(target),
      tag:target.tagName.toLowerCase(),
      text:directText(target),
      image:target instanceof HTMLImageElement?target.src:'',
      alt:target instanceof HTMLImageElement?target.alt:'',
    },editorParentOrigin);
  },true);
}
const heroCarousel=pageKey==='home'?document.querySelector('.hero-visual'):null;
if(heroCarousel){
  heroCarousel.classList.add('hero-carousel');
  heroCarousel.setAttribute('role','region');
  heroCarousel.setAttribute('aria-roledescription','carousel');
  heroCarousel.setAttribute('aria-label','Featured Esicom supplies, printing and branding');
  const initialImage=heroCarousel.querySelector('[data-copy-image]');
  initialImage.removeAttribute('data-copy-image');
  initialImage.setAttribute('data-hero-slide-image','');
  initialImage.src='/images/photography/stock-office-box.webp';
  initialImage.alt='Boxed workplace supplies ready for an office';
  const note=document.createElement('div');
  note.className='floating-note';
  note.textContent='SUPPLY · PRINT · BRAND';
  const slideLink=document.createElement('a');
  slideLink.className='hero-slide-link';
  slideLink.setAttribute('data-hero-slide-link','');
  slideLink.href='/office-supplies/';
  slideLink.append(initialImage);
  const caption=document.createElement('div');
  caption.className='visual-caption';
  const captionCopy=document.createElement('div');
  captionCopy.className='hero-caption-copy';
  const captionCategory=document.createElement('small');
  captionCategory.setAttribute('data-hero-slide-category','');
  const captionTitle=document.createElement('strong');
  captionTitle.setAttribute('data-hero-slide-title','');
  captionCopy.append(captionCategory,captionTitle);
  const slideMore=document.createElement('a');
  slideMore.className='hero-slide-more';
  slideMore.setAttribute('data-hero-slide-more','');
  slideMore.href='/office-supplies/';
  slideMore.textContent='Explore ↗';
  caption.append(captionCopy,slideMore);
  const controls=document.createElement('div');
  controls.className='hero-carousel-controls';
  controls.setAttribute('aria-label','Photo slideshow controls');
  const previous=document.createElement('button');
  previous.type='button';
  previous.setAttribute('data-hero-previous','');
  previous.setAttribute('aria-label','Previous photo');
  previous.textContent='←';
  const dots=document.createElement('div');
  dots.setAttribute('data-hero-dots','');
  dots.setAttribute('aria-label','Choose a photo');
  const next=document.createElement('button');
  next.type='button';
  next.setAttribute('data-hero-next','');
  next.setAttribute('aria-label','Next photo');
  next.textContent='→';
  const toggle=document.createElement('button');
  toggle.type='button';
  toggle.setAttribute('data-hero-toggle','');
  controls.append(previous,dots,next,toggle);
  heroCarousel.replaceChildren(note,slideLink,caption,controls);
}
const imageSlides=[
  {image:'/images/photography/stock-office-box.webp',alt:'Boxed workplace supplies ready for an office',category:'Supply · Office essentials',title:'Everyday supplies, brought together.',href:'/office-supplies/'},
  {image:'/images/photography/computer.webp',alt:'Computer and printer workspace',category:'Supply · Computer essentials',title:'The essentials behind a productive team.',href:'/computer-consumables/'},
  {image:'/images/photography/printing.webp',alt:'Printed materials prepared for a business brief',category:'Print · Business printing',title:'Make your next print run stand out.',href:'/bulk-printing/'},
  {image:'/images/photography/apparel.webp',alt:'Apparel for a corporate branding enquiry',category:'Brand · Corporate identity',title:'Put your organisation’s identity to work.',href:'/branding/'}
];
let carouselSlides=imageSlides;
let carouselActive=0;
let carouselTimer=null;
let carouselTransition=null;
let carouselPaused=visualEditorMode||window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let homePageImage='';
let visualEditsCache=[];
const showHeroSlide=index=>{
  if(!heroCarousel||!carouselSlides.length)return;
  const image=heroCarousel.querySelector('[data-hero-slide-image]');
  const slideLink=heroCarousel.querySelector('[data-hero-slide-link]');
  const slideMore=heroCarousel.querySelector('[data-hero-slide-more]');
  const category=heroCarousel.querySelector('[data-hero-slide-category]');
  const title=heroCarousel.querySelector('[data-hero-slide-title]');
  const dots=heroCarousel.querySelector('[data-hero-dots]');
  carouselActive=(index+carouselSlides.length)%carouselSlides.length;
  const slide=carouselSlides[carouselActive];
  image.classList.add('is-changing');
  window.clearTimeout(carouselTransition);
  const renderSlide=()=>{
    image.src=siteImage(slide.image);
    image.alt=slide.alt;
    slideLink.href=slide.href;
    slideMore.href=slide.href;
    category.textContent=slide.category;
    title.textContent=slide.title;
    image.classList.remove('is-changing');
    if(carouselActive===0&&heroCarousel){applyVisualEdits(visualEditsCache.filter(e=>{const t=document.querySelector(e.selector);return t&&heroCarousel.contains(t);}));}
  };
  if(visualEditorMode)renderSlide();
  else carouselTransition=window.setTimeout(renderSlide,150);
  for(const [dotIndex,button] of [...dots.children].entries()){
    button.setAttribute('aria-current',String(dotIndex===carouselActive));
    button.setAttribute('aria-label','Show photo '+(dotIndex+1)+' of '+carouselSlides.length);
  }
};
const setHeroPaused=nextPaused=>{
  if(!heroCarousel)return;
  const pauseButton=heroCarousel.querySelector('[data-hero-toggle]');
  carouselPaused=nextPaused;
  pauseButton.setAttribute('aria-pressed',String(carouselPaused));
  pauseButton.setAttribute('aria-label',carouselPaused?'Play photo slideshow':'Pause photo slideshow');
  pauseButton.textContent=carouselPaused?'▶':'Ⅱ';
  window.clearInterval(carouselTimer);
  if(!carouselPaused&&carouselSlides.length>1)carouselTimer=window.setInterval(()=>showHeroSlide(carouselActive+1),5500);
};
const startHeroCarousel=featuredProducts=>{
  if(!heroCarousel)return;
  const dots=heroCarousel.querySelector('[data-hero-dots]');
  const productSlides=featuredProducts.map(product=>({
    image:imageUrl(product.image),
    alt:product.name,
    category:'Featured · '+(product.page==='office-supplies'?'Office essentials':product.page.replaceAll('-',' ')),
    title:product.name,
    href:'/'+encodeURIComponent(product.page)+'/'
  }));
  carouselSlides=homePageImage
    ?[{image:imageUrl(homePageImage),alt:'Featured Esicom Suppliers photo',category:'ESICOM · SUPPLY. PRINT. BRAND.',title:'The details that keep your workday moving.',href:'/office-supplies/'},...(productSlides.length?productSlides:imageSlides)]
    :productSlides.length?productSlides:imageSlides;
  dots.replaceChildren(...carouselSlides.map((slide,index)=>{
    const button=document.createElement('button');
    button.type='button';
    button.setAttribute('aria-label','Show photo '+(index+1)+' of '+carouselSlides.length);
    button.setAttribute('aria-current',String(index===0));
    button.addEventListener('click',()=>showHeroSlide(index));
    return button;
  }));
  showHeroSlide(0);
  setHeroPaused(carouselPaused);
};
if(heroCarousel){
  heroCarousel.querySelector('[data-hero-previous]').addEventListener('click',()=>showHeroSlide(carouselActive-1));
  heroCarousel.querySelector('[data-hero-next]').addEventListener('click',()=>showHeroSlide(carouselActive+1));
  heroCarousel.querySelector('[data-hero-toggle]').addEventListener('click',()=>setHeroPaused(!carouselPaused));
  heroCarousel.addEventListener('mouseenter',()=>window.clearInterval(carouselTimer));
  heroCarousel.addEventListener('mouseleave',()=>{if(!carouselPaused&&carouselSlides.length>1)carouselTimer=window.setInterval(()=>showHeroSlide(carouselActive+1),5500)});
}
startHeroCarousel([]);
const productCard=product=>{
  const article=document.createElement('article');
  article.className='card';
  article.dataset.editorKey='product-'+product.slug;
  const link=document.createElement('a');
  link.href='/'+encodeURIComponent(product.page)+'/';
  const image=document.createElement('img');
  image.src=imageUrl(product.image);
  image.alt=product.name;
  image.loading='lazy';
  image.decoding='async';
  const body=document.createElement('div');
  body.className='card-body';
  const heading=document.createElement('h3');
  heading.textContent=product.name;
  const description=document.createElement('p');
  description.textContent=product.description;
  const more=document.createElement('span');
  more.className='link';
  more.textContent='Ask us about this';
  body.append(heading,description,more);
  link.append(image,body);
  article.append(link);
  return article;
};
const editableSection=section=>{
  const wrapper=document.createElement('section');
  wrapper.className='section editable-section';
  wrapper.dataset.editorKey='section-'+section.id;
  const content=document.createElement('div');
  content.className='wrap editable-section-card';
  if(section.image){
    const image=document.createElement('img');
    image.src=imageUrl(section.image);
    image.alt=section.title;
    image.loading='lazy';
    image.decoding='async';
    content.append(image);
  }
  const copy=document.createElement('div');
  copy.className='editable-section-copy';
  const heading=document.createElement('h2');
  heading.textContent=section.title;
  copy.append(heading);
  if(section.body){
    const body=document.createElement('p');
    body.textContent=section.body;
    copy.append(body);
  }
  if(section.button_text&&section.button_url){
    const button=document.createElement('a');
    button.className='btn btn-primary';
    button.href=section.button_url;
    button.textContent=section.button_text;
    copy.append(button);
  }
  content.append(copy);
  wrapper.append(content);
  return wrapper;
};
const loadSiteContent=async()=>{
  if(!main)return;
  const response=await fetch(apiBase+'/api/site-content/',{headers:{'Accept':'application/json'},cache:'no-store'});
  if(!response.ok)throw new Error('Site content service returned HTTP '+response.status);
  const content=await response.json();
  photoOverrides=content.photos||{};
  visualEditsCache=content.visual_edits||[];
  document.querySelectorAll('img[src]').forEach(image=>{
    const source=image.getAttribute('src');
    if(source&&photoOverrides[source])image.src=imageUrl(photoOverrides[source]);
  });
  const page=content.pages?.[pageKey];
  if(page){
    const eyebrow=main.querySelector('[data-copy-eyebrow]');
    if(eyebrow)eyebrow.textContent=page.eyebrow;
    const intro=main.querySelector('[data-copy-intro]');
    if(intro)intro.textContent=page.intro;
    const heading=main.querySelector('[data-copy-heading]');
    if(heading){
      const highlight=heading.querySelector('[data-copy-highlight]');
      if(highlight){
        const leadingText=[...heading.childNodes].find(node=>node.nodeType===Node.TEXT_NODE);
        if(leadingText)leadingText.textContent=page.title;
        highlight.textContent=page.highlight||'';
        highlight.hidden=!page.highlight;
      }else heading.textContent=page.title;
    }
    if(page.image){
      if(pageKey==='home')homePageImage=page.image;
      else{
        const heroImage=main.querySelector('[data-copy-image]');
        if(heroImage)heroImage.src=imageUrl(page.image);
      }
    }
  }
  const products=Array.isArray(content.products)?content.products:[];
  if(pageKey==='home'){
    const featured=products.filter(product=>product.featured);
    const container=main.querySelector('[data-featured-products]');
    if(container)container.replaceChildren(...featured.map(productCard));
    startHeroCarousel(featured);
  }else{
    const categoryProducts=products.filter(product=>product.page===pageKey);
    const section=main.querySelector('[data-category-products]');
    const container=section?.querySelector('[data-product-list]');
    if(container&&categoryProducts.length){
      container.replaceChildren(...categoryProducts.map(productCard));
      section.hidden=false;
    }
  }
  const sections=(Array.isArray(content.sections)?content.sections:[])
    .filter(section=>section.page===pageKey)
    .map(editableSection);
  main.append(...sections);
  applyVisualEdits(content.visual_edits||[]);
};
loadSiteContent().catch(error=>{
  console.info('Site editor is not connected; showing the built-in page content.',error);
});
document.querySelectorAll('[data-quote-form]').forEach(form=>form.addEventListener('submit',async e=>{
  e.preventDefault();
  const btn=form.querySelector('button[type=submit]');
  const status=form.querySelector('[data-form-status]');
  const fd=new FormData(form);
  const data=Object.fromEntries(fd.entries());
  const base=(window.ESICOM_API_BASE_URL||'').replace(/\/$/,'');
  btn.disabled=true;
  btn.textContent='Submitting…';
  status.textContent='';
  try{
    const response=await fetch(base+'/api/quote/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:data.name,company:data.company||'',email:data.email||'',phone:data.phone,needs:(data.service||'Business supplies')+': '+data.details,quantity:data.quantity||'',date:data.date||'',source:'website'})});
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(result.detail||'The quote service is temporarily unavailable.');
    status.textContent='Thank you. Your enquiry has been recorded. Reference: ES-'+result.reference+'. We will follow up using the details provided.';
    form.reset();
  }catch(err){
    const subject=encodeURIComponent('Esicom quote request — '+(data.service||'Business supplies'));
    const body=encodeURIComponent('Hello Esicom Suppliers,\n\nName: '+data.name+'\nOrganisation: '+(data.company||'Not provided')+'\nPhone: '+data.phone+'\nEmail: '+(data.email||'Not provided')+'\nRequirement: '+(data.service||'Business supplies')+'\nDetails: '+data.details+'\nQuantity: '+(data.quantity||'Not specified')+'\nRequired date: '+(data.date||'Not specified'));
    status.textContent=err.message+' An email draft will open as a fallback. If it does not open, email esicomsuppliers@gmail.com.';
    window.location.href='mailto:esicomsuppliers@gmail.com?subject='+subject+'&body='+body;
  }finally{
    btn.disabled=false;
    btn.textContent='Send your enquiry ↗';
  }
}));
const uploadForm=document.querySelector('[data-file-upload-form]');
if(uploadForm){
  const fileInput=uploadForm.querySelector('[name=file]');
  const conversionField=uploadForm.querySelector('[data-conversion-field]');
  const conversionSelect=uploadForm.querySelector('[name=conversion]');
  const submitButton=uploadForm.querySelector('[type=submit]');
  const status=uploadForm.querySelector('[data-upload-status]');
  const resultPanel=document.querySelector('[data-upload-result]');
  const downloadLink=resultPanel.querySelector('[data-upload-download]');
  const shareButton=resultPanel.querySelector('[data-upload-share]');
  const whatsappLink=resultPanel.querySelector('[data-upload-whatsapp]');
  const deliveryInputs=uploadForm.querySelectorAll('[name=delivery]');
  const fileSizeNote=uploadForm.querySelector('[data-file-size-note]');
  const updateDeliveryUi=()=>{
    const isEmail=selectedDelivery()==='email';
    fileSizeNote.textContent=isEmail
      ?'Email attachments up to 15 MB · Choose WhatsApp to share larger files.'
      :'Files up to 50 MB · WhatsApp sharing requires confirmation in your messaging app.';
    submitButton.textContent=isEmail?'Email file to Esicom':'Prepare file for WhatsApp';
  };
  let completedSubmission=null;
  let completedShareFile=null;
  const selectedDelivery=()=>uploadForm.querySelector('[name=delivery]').value||'email';
  deliveryInputs.forEach(input=>input.addEventListener('change',updateDeliveryUi));
  updateDeliveryUi();
  fileInput.addEventListener('change',()=>{
    const file=fileInput.files[0];
    conversionSelect.replaceChildren(new Option('Send original file',''));
    conversionField.hidden=true;
    completedSubmission=null;
    completedShareFile=null;
    if(!file)return;
    const extension=file.name.split('.').pop().toLowerCase();
    const conversions=extension==='pdf'
      ?[['docx','Word document (.docx)']]
      :['jpg','jpeg','png','webp'].includes(extension)
        ?[['jpeg','JPEG (.jpg)'],['png','PNG (.png)'],['webp','WebP (.webp)']]
        :[];
    conversions.forEach(([value,label])=>conversionSelect.add(new Option(label,value)));
    conversionField.hidden=!conversions.length;
    resultPanel.hidden=true;
    status.textContent='';
  });
  uploadForm.addEventListener('submit',async event=>{
    event.preventDefault();
    const file=fileInput.files[0];
    if(!file)return;
    const delivery=selectedDelivery();
    const maxBytes=delivery==='email'?15*1024*1024:50*1024*1024;
    if(file.size>maxBytes){
      status.textContent=delivery==='email'
        ?'Email attachments must be 15 MB or smaller. Choose WhatsApp to share larger files.'
        :'Choose a file that is 50 MB or smaller.';
      return;
    }
    submitButton.disabled=true;
    submitButton.textContent=delivery==='email'?'Sending email attachment…':'Preparing WhatsApp file…';
    status.textContent='';
    resultPanel.hidden=true;
    try{
      const payload=new FormData(uploadForm);
      payload.set('delivery',delivery);
      const response=await fetch(apiBase+'/api/file-submissions/',{method:'POST',body:payload});
      const result=await response.json().catch(()=>({}));
      if(!response.ok){
        const error=new Error(result.detail||'The file upload service is unavailable.');
        error.saved=Boolean(result.saved);
        error.reference=result.reference;
        throw error;
      }
      const downloadUrl=new URL(result.download_url,apiBase?apiBase+'/':location.origin).href;
      completedSubmission={...result,downloadUrl};
      completedShareFile=result.converted?null:file;
      const supportsFileShare=sharedFile=>navigator.share&&navigator.canShare&&navigator.canShare({files:[sharedFile]});
      shareButton.hidden=delivery!=='whatsapp'||(!result.converted&&!supportsFileShare(file));
      shareButton.disabled=Boolean(result.converted);
      shareButton.textContent=result.converted?'Preparing share file…':'Share file…';
      whatsappLink.hidden=delivery!=='whatsapp';
      downloadLink.href=downloadUrl;
      downloadLink.textContent='Download '+result.filename;
      whatsappLink.href='https://wa.me/254728942669?text='+encodeURIComponent('Hello Esicom Suppliers, I submitted file reference ES-F'+result.reference+'.');
      resultPanel.querySelector('[data-upload-confirmation]').textContent=delivery==='email'
        ?'Your file was emailed to Esicom as an attachment. Reference: ES-F'+result.reference+'. A private backup copy stays available until staff deletes the submission.'
        :'Your file is ready to share. Choose Share file, select WhatsApp and Esicom, then confirm Send. Reference: ES-F'+result.reference+'.';
      resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=delivery!=='whatsapp';
      resultPanel.hidden=false;
      uploadForm.reset();
      conversionField.hidden=true;
      updateDeliveryUi();
      status.textContent='';
      if(result.converted&&navigator.share&&navigator.canShare){
        fetch(downloadUrl).then(response=>{
          if(!response.ok)throw new Error('The prepared file could not be downloaded.');
          return response.blob();
        }).then(blob=>{
          completedShareFile=new File([blob],result.filename,{type:blob.type||'application/octet-stream'});
          if(supportsFileShare(completedShareFile)){
            shareButton.hidden=false;
            shareButton.disabled=false;
            shareButton.textContent='Share file…';
          }else{
            shareButton.hidden=true;
            resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
          }
        }).catch(error=>{
          shareButton.hidden=true;
          shareButton.disabled=true;
          status.textContent=error.message+' You can still download the file and attach it in WhatsApp.';
          resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
        });
      }else if(result.converted){
        shareButton.hidden=true;
        resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
      }
    }catch(error){
      status.textContent=error.saved
        ?error.message
        :error.message+' Your file has not been confirmed as sent; please try again.';
    }finally{
      submitButton.disabled=false;
      updateDeliveryUi();
    }
  });
  shareButton.addEventListener('click',()=>{
    if(!completedSubmission||!completedShareFile)return;
    try{
      if(!navigator.share||!navigator.canShare||!navigator.canShare({files:[completedShareFile]})){
        status.textContent='Your file is ready. Download it, open WhatsApp, and attach the file to your message.';
        return;
      }
      navigator.share({files:[completedShareFile],title:'File for Esicom Suppliers',text:'File submission ES-F'+completedSubmission.reference}).catch(error=>{
        if(error.name!=='AbortError')status.textContent=error.message||'File sharing is unavailable in this browser. Download the file and attach it in WhatsApp.';
      });
    }catch(error){
      if(error.name!=='AbortError')status.textContent=error.message||'File sharing is unavailable in this browser. Download the file and attach it in WhatsApp.';
    }
  });
}
const qrImage=document.querySelector('[data-upload-qr]');
if(qrImage){
  const qrUrl=apiBase+'/api/file-upload-qr/';
  qrImage.src=qrUrl;
  const downloadQr=document.querySelector('[data-qr-download]');
  if(downloadQr)downloadQr.href=qrUrl;
}
document.querySelector('[data-print-qr]')?.addEventListener('click',()=>window.print());
})();'''

NAV = [('/office-supplies/','Office supplies'),('/computer-consumables/','Computer consumables'),('/bulk-printing/','Bulk printing'),('/branding/','Branding'),('/about/','About'),('/contact/','Contact'),('/send-file/','Send a file')]

def esc(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def header(path):
    links=''.join(f'<a href="{href}"'+(' aria-current="page"' if path==href else '')+f'>{label}</a>' for href,label in NAV)
    return f'''<a class="skip-link" href="#main-content">Skip to main content</a><div class="topline"><div class="wrap"><span>SUPPLY. PRINT. BRAND.</span><span>Chaka Place Building · Nairobi, Kenya &nbsp; | &nbsp; <a href="mailto:esicomsuppliers@gmail.com">esicomsuppliers@gmail.com</a></span></div></div><header class="header"><div class="wrap navrow"><a class="brand" href="/" aria-label="Esicom Suppliers home"><span class="brand-mark">E.</span><span><span class="brand-name">ESICOM</span><span class="brand-sub">Suppliers</span></span></a><nav class="navlinks" aria-label="Main navigation">{links}</nav><div class="nav-actions"><a class="btn btn-light catalogue-btn" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Catalogue ↓</a><a class="btn btn-primary quote-btn" href="/contact/">Request a quote ↗</a><button class="menu-btn" data-menu-button aria-controls="mobile-navigation" aria-expanded="false" aria-label="Open navigation">☰</button></div></div><nav class="mobile-nav" id="mobile-navigation" data-mobile-nav aria-label="Mobile navigation">{links}<a href="/catalogue/esicom-suppliers-catalogue.pdf" download>Download product catalogue (PDF)</a><a href="/contact/">Request a quote ↗</a></nav></header>'''

def footer():
    return '''<footer class="footer"><div class="wrap"><div class="footer-grid"><div><a class="brand" href="/" style="color:white"><span class="brand-mark" style="background:#fff;color:#10243d">E.</span><span><span class="brand-name">ESICOM</span><span class="brand-sub" style="color:#b9c8d8">Suppliers</span></span></a><p style="max-width:290px;line-height:1.8">Office essentials, computer consumables, bulk printing and corporate branding.</p><p style="font:800 18px Manrope,sans-serif;color:white">SUPPLY. PRINT. BRAND.</p></div><div><h3>Products</h3><div class="footer-links"><a href="/office-supplies/">Office supplies</a><a href="/paper-filing/">Paper & filing</a><a href="/computer-consumables/">Computer consumables</a><a href="/catalogue/esicom-suppliers-catalogue.pdf" download>Product catalogue (PDF)</a></div></div><div><h3>Services</h3><div class="footer-links"><a href="/bulk-printing/">Bulk printing</a><a href="/branding/">Corporate branding</a><a href="/business-cards/">Business cards</a><a href="/branded-apparel/">Branded apparel</a><a href="/diaries-asset-tags/">Diaries & asset tags</a><a href="/send-file/">Send a file</a><a href="/file-qr/">Print the file QR</a></div></div><div><h3>Contact</h3><div class="footer-links"><a href="mailto:esicomsuppliers@gmail.com">esicomsuppliers@gmail.com</a><a href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20have%20an%20enquiry." target="_blank" rel="noopener noreferrer">WhatsApp · 0728 942 669</a><p>Chaka Place Building,<br>Arwings Kodhek Road,<br>Nairobi, Kenya</p><a href="https://www.google.com/maps/search/?api=1&query=Chaka+Place+Building%2C+Arwings+Kodhek+Road%2C+Nairobi%2C+Kenya" target="_blank" rel="noopener noreferrer">Open location in Maps ↗</a><a href="/admin/" rel="nofollow">Staff content editor ↗</a></div></div></div><div class="footer-bottom"><span>© <span data-year></span> Esicom Suppliers. All rights reserved.</span><span>Product availability and quotations confirmed on enquiry.</span></div></div></footer><a class="whatsapp" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20to%20make%20an%20enquiry." target="_blank" rel="noopener noreferrer" aria-label="Chat with Esicom Suppliers on WhatsApp">◉ WhatsApp us</a><script>document.querySelector('[data-year]').textContent=new Date().getFullYear()</script><script src="/site.js?v=5" defer></script>'''

def catalogue_callout():
    return '<div class="catalogue-callout"><div><strong>Prefer a quick overview?</strong><p>Download the product and services catalogue as a PDF.</p></div><a class="btn btn-primary" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Download catalogue ↓</a></div>'

def quote_form():
    return '''<form class="quote-form" data-quote-form><h2>Let’s start with your brief</h2><p>Tell us a little about what your team needs. We’ll follow up to talk through the details.</p><div class="form-grid"><label class="field">Full name *<input name="name" required minlength="2" maxlength="120" autocomplete="name" placeholder="Your full name"></label><label class="field">Organisation<input name="company" maxlength="160" autocomplete="organization" placeholder="Company or organisation"></label><label class="field">Phone number *<input name="phone" required maxlength="40" autocomplete="tel" placeholder="Your best contact number"></label><label class="field">Email address<input name="email" type="email" maxlength="254" autocomplete="email" placeholder="you@example.com"></label><label class="field full">What do you need? *<select name="service" required><option value="Office supplies">Office supplies</option><option value="Computer consumables">Computer consumables</option><option value="Bulk printing">Bulk printing</option><option value="Corporate branding">Corporate branding</option><option value="Business cards">Business cards</option><option value="Branded apparel">Branded apparel</option><option value="Diaries and asset tags">Diaries and asset tags</option><option value="Other requirement">Other requirement</option></select></label><label class="field">Estimated quantity<input name="quantity" maxlength="100" placeholder="If known"></label><label class="field">Required date<input name="date" type="date"></label><label class="field full">Tell us more *<textarea name="details" required minlength="8" maxlength="5000" placeholder="Add product names, quantities, specifications, artwork or timing."></textarea></label></div><button type="submit" class="btn btn-primary" style="width:100%;margin-top:20px">Send your enquiry ↗</button><a class="btn btn-light" style="width:100%;margin-top:10px" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20a%20quote." target="_blank" rel="noopener noreferrer">Continue on WhatsApp ↗</a><div class="form-status" data-form-status role="status" aria-live="polite"></div><p style="margin-top:12px;font-size:11px">Prefer email? <a href="mailto:esicomsuppliers@gmail.com"><b>esicomsuppliers@gmail.com</b></a></p></form>'''

def card(href, image, title, desc, label='Explore details', credit=None):
    credit_html=f'<small class="photo-credit">{credit}</small>' if credit else ''
    return f'<article class="card"><a href="{href}"><img src="{image}" alt="{esc(title)}" loading="lazy"><div class="card-body"><h3>{esc(title)}</h3><p>{esc(desc)}</p><span class="link">{label}</span></div></a>{credit_html}</article>'

def home_content():
    products=card('/office-supplies/','/images/photography/stock-boxed-pens.webp','Packaged pen','A real packaged pen. Ask us about the pens and everyday stationery your team needs.',credit='<a href="https://commons.wikimedia.org/wiki/File:Colorex_in_Verpackung.jpg" target="_blank" rel="noopener noreferrer">Photo: Oliver Laumann · CC BY-SA 4.0</a>')+card('/computer-consumables/','/images/photography/computer.webp','Computer consumables','Toners, cartridges and computer essentials. Tell us your printer model.')+card('/paper-filing/','/images/photography/stock-copy-paper.webp','Copy paper by the ream','A real photo of copy-paper reams. Ask us about paper sizes and quantities.',credit='<a href="https://commons.wikimedia.org/wiki/File:6_reams_of_paper_stacked_on_the_floor.jpg" target="_blank" rel="noopener noreferrer">Photo: Sage Ross · CC BY-SA 3.0</a>')
    services='''<a class="service-feature" href="/bulk-printing/"><img src="/images/photography/printing.webp" alt="Printed pages prepared for a business print job" loading="lazy"><div><h3>Bulk printing</h3><p>Business documents and printed materials, planned around your brief.</p><span class="link" style="color:#fff">Explore printing</span></div></a><a class="service-feature" href="/branding/"><img src="/images/photography/apparel.webp" alt="Plain shirt ready for a branded apparel enquiry" loading="lazy"><div><h3>Corporate branding</h3><p>Business cards, apparel, diaries and the details that carry your identity.</p><span class="link" style="color:#fff">Explore branding</span></div></a><a class="service-feature" href="/about/"><img src="/images/photography/meeting-room.webp" alt="Bright modern meeting room" loading="lazy"><div><h3>One helpful point of contact</h3><p>Office supplies, printing and branding brought together in Nairobi.</p><span class="link" style="color:#fff">Get to know Esicom</span></div></a>'''
    branded=card('/business-cards/','/images/photography/printing.webp','Business cards','Printed details that help your team make a consistent first impression.')+card('/branded-apparel/','/images/photography/apparel.webp','Branded apparel','An easy way to bring your team’s identity together.')+card('/diaries-asset-tags/','/images/photography/stationery.webp','Diaries & asset tags','Practical branded stationery and identification enquiries.')
    return f'''<main><section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow" data-copy-eyebrow>A Nairobi supplier for the workday</div><h1 data-copy-heading>Everything your office<br><span data-copy-highlight>needs.</span></h1><p class="lead" data-copy-intro>Everyday stationery, printing supplies and branded merchandise. Tell us what you need; we’ll take it from there.</p><div class="actions"><a class="btn btn-primary" href="/contact/">Tell us what you need ↗</a><a class="btn btn-light" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Browse the catalogue ↓</a></div><div style="margin-top:25px"><span class="mockup-label">Chaka Place · Nairobi, Kenya</span></div></div><div class="hero-visual"><div class="floating-note">Your local business supplier</div><img data-copy-image src="/images/photography/workspace.webp" alt="Bright, organized office workspace" fetchpriority="high" decoding="async"><div class="visual-caption">Office essentials. Printing. Your brand.</div></div></div></section><section class="strip"><div class="wrap strip-grid"><div class="strip-item"><b>01</b><span>Office & workplace</span></div><div class="strip-item"><b>02</b><span>Computer essentials</span></div><div class="strip-item"><b>03</b><span>Business printing</span></div><div class="strip-item"><b>04</b><span>Corporate branding</span></div></div></section><section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">SUPPLY · THE EVERYDAY ESSENTIALS</div><h2>The things every office runs on.</h2></div><p>Boxes of pens, reams of paper and the essentials your team reaches for every day. Tell us what you need and we’ll put together a quote.</p></div><div class="cards" data-featured-products>{products}</div>{catalogue_callout()}</div></section><section class="section dark"><div class="wrap"><div class="section-head"><div><div class="eyebrow">PRINT · BRAND · Bring your brief</div><h2>Print, paper and branded merchandise.</h2></div><p>Send us your artwork, list or logo. We’ll help you work through the details.</p></div><div class="service-panel premium-services">{services}</div></div></section><section class="section white"><div class="wrap"><div class="section-head"><div><div class="eyebrow">BRAND · THE LITTLE THINGS</div><h2>Put your name on something useful.</h2></div><p>From shirts and diaries to everyday stationery, ask us about branded items for your team.</p></div><div class="cards">{branded}</div></div></section><section class="section"><div class="wrap"><div class="cta-band"><div><div class="eyebrow">A simpler next step</div><h2>Have a list or a logo?</h2><p style="margin:0;color:var(--muted)">Send it over. We’ll help you take it from there.</p></div><a class="btn btn-primary" href="/contact/">Start a conversation ↗</a></div></div></section></main>'''

def detail_content(path,data):
    items=data.get('items',[])
    if data['kind']=='branding':
        cards=card('/business-cards/','/images/photography/printing.webp','Business cards','Professional business card enquiries for meetings, introductions and networking.')+card('/branded-apparel/','/images/photography/apparel.webp','Branded shirts','Branded apparel enquiries for teams, events and everyday use.')+card('/diaries-asset-tags/','/images/photography/stationery.webp','Diaries & asset tags','Practical branded stationery and identification materials.')
        extra=f'<section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">Explore branding</div><h2>Choose a starting point.</h2></div><p>Photography is illustrative, not a portfolio of completed customer projects. Share your artwork and requirements for a tailored quotation.</p></div><div class="cards">{cards}</div></div></section>'
    else: extra=''
    lis=''.join(f'<div class="check-item">{esc(x)}</div>' for x in items)
    return f'''<main><section class="page-hero"><div class="wrap page-hero-grid"><div><div class="eyebrow" data-copy-eyebrow>{esc(data['eyebrow'])}</div><h1 data-copy-heading>{esc(data['title'])}</h1><p data-copy-intro>{esc(data['intro'])}</p><div class="actions"><a class="btn btn-primary" href="/contact/">Tell us what you need ↗</a><a class="btn btn-light" href="/catalogue/esicom-suppliers-catalogue.pdf" download>View the catalogue ↓</a></div></div><img data-copy-image src="{data['image']}" alt="Photograph illustrating {esc(data['eyebrow'].lower())}" loading="eager" decoding="async"></div></section><section class="section"><div class="wrap detail-grid"><div><div class="eyebrow">What do you need?</div><h2 style="font:800 clamp(29px,4vw,45px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:15px 0">Send us a list.<br><span style="color:var(--blue)">We’ll take it from there.</span></h2><p style="color:var(--muted);line-height:1.85">Add the sizes, quantities or product details you already know. We’ll follow up if we need anything else.</p><a class="btn btn-primary" href="/contact/">Ask us for a quote ↗</a></div><div class="check-list">{lis}</div></div></section><section class="section category-products" data-category-products data-category="{path.strip('/')}" hidden><div class="wrap"><div class="section-head"><div><div class="eyebrow">IN THE CATALOGUE</div><h2>Products we can help you source.</h2></div></div><div class="cards" data-product-list></div></div></section>{extra}<section class="section white"><div class="wrap"><div class="cta-band"><div><div class="eyebrow">A simpler next step</div><h2>Have a list or a logo?</h2><p style="margin:0;color:var(--muted)">Send it over. We’ll help you take it from there.</p></div><a class="btn btn-primary" href="/contact/">Start a conversation ↗</a></div></div></section></main>'''

def contact_content(data):
    return f'''<main><section class="page-hero"><div class="wrap page-hero-grid"><div><div class="eyebrow" data-copy-eyebrow>{data['eyebrow']}</div><h1 data-copy-heading>{data['title']}</h1><p data-copy-intro>{data['intro']}</p><span class="mockup-label">Chaka Place · Nairobi, Kenya</span></div><img data-copy-image src="{data['image']}" alt="A light-filled contemporary workspace" loading="eager" decoding="async"></div></section><section class="section"><div class="wrap form-layout"><div><div class="eyebrow">Contact Esicom</div><h2 style="font:800 clamp(30px,4vw,46px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:15px 0">A real conversation starts here.</h2><p style="color:var(--muted);line-height:1.8">Call, write or send a note about what your team needs. We’re based at Chaka Place in Nairobi.</p><div class="contact-list"><a class="contact-item" href="mailto:esicomsuppliers@gmail.com"><span class="contact-icon">✉</span><span><small>Email us</small><b>esicomsuppliers@gmail.com</b></span></a><a class="contact-item" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20to%20discuss%20a%20quotation." target="_blank" rel="noopener noreferrer"><span class="contact-icon">◉</span><span><small>WhatsApp enquiries</small><b>0728 942 669</b></span></a><div class="contact-item"><span class="contact-icon">⌖</span><span><small>Visit us</small><b>Chaka Place Building, Arwings Kodhek Road</b><small>Nairobi, Kenya</small></span></div><a class="link" href="https://www.google.com/maps/search/?api=1&query=Chaka+Place+Building%2C+Arwings+Kodhek+Road%2C+Nairobi%2C+Kenya" target="_blank" rel="noopener noreferrer">Open location in Maps ↗</a></div></div>{quote_form()}</div></section></main>'''

def upload_content():
    return '''<main><section class="upload-shell"><div class="wrap upload-grid"><form class="upload-card" data-file-upload-form><div class="eyebrow">SEND A FILE</div><h1>Share a file with Esicom.</h1><p>Choose a file, select email or WhatsApp, then send it to our team.</p><label class="field">File *<input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png,.webp" required></label><p class="upload-note" data-file-size-note>Email attachments up to 15 MB · Choose WhatsApp to share larger files.</p><label class="field">Send using<select name="delivery"><option value="email">Email the file to Esicom</option><option value="whatsapp">Share the file with Esicom on WhatsApp</option></select></label><label class="field" data-conversion-field hidden>Convert to<select name="conversion"><option value="">Send original file</option></select></label><label class="field">Your name (optional)<input name="name" maxlength="120" autocomplete="name"></label><label class="field">Phone number (optional)<input name="phone" maxlength="40" autocomplete="tel"></label><label class="field">Message for Esicom (optional)<textarea name="note" maxlength="500" rows="3" placeholder="Add a short note about your file"></textarea></label><label class="field"><input type="checkbox" name="delivery_consent" required> I agree to send this file to Esicom using the delivery method selected above.</label><div aria-hidden="true" style="position:absolute;left:-10000px"><label>Leave this empty<input name="website" tabindex="-1" autocomplete="off"></label></div><button type="submit" class="btn btn-primary" style="width:100%;margin-top:20px">Email file to Esicom</button><p class="upload-note">PDF, JPG, PNG or WebP · Files stay private until Esicom staff deletes them.</p><div class="form-status" data-upload-status role="status" aria-live="polite"></div></form><aside class="upload-card"><div class="eyebrow">WHAT HAPPENS NEXT</div><h2>Email or WhatsApp.</h2><p>Email sends the actual file as an attachment to Esicom. WhatsApp opens your phone’s share screen; choose WhatsApp and the Esicom chat, then tap Send.</p><p class="upload-note">Email attachments are limited to 15 MB so email providers can accept them. WhatsApp sharing supports files up to 50 MB. PDF-to-Word conversion is best-effort and may change complex layouts; scanned PDFs need OCR for editable text.</p><a class="link" href="/file-qr/">Get the printable QR code ↗</a><div class="upload-result" data-upload-result hidden><p data-upload-confirmation role="status"></p><a class="btn btn-light" data-upload-download href="#">Download file</a><button type="button" class="btn btn-primary" data-upload-share hidden>Share file…</button><a class="btn btn-light" data-upload-whatsapp target="_blank" rel="noopener noreferrer">Open WhatsApp</a><p class="upload-note" data-upload-whatsapp-note hidden>If file sharing is unavailable in your browser, download the file and attach it to the Esicom WhatsApp chat.</p></div></aside></div></section></main>'''

def file_qr_content():
    return '''<main><section class="qr-shell"><div class="wrap"><div class="qr-card"><div class="eyebrow" style="justify-content:center">ESICOM SUPPLIERS · FILE UPLOAD</div><h1>Scan to send us a file.</h1><p class="qr-instructions">Scan this code with a phone camera to open our upload page. Customers can attach a PDF or photo, convert it if needed, and send it securely to our team.</p><img class="qr-image" data-upload-qr alt="QR code linking to the Esicom file upload page"><p class="upload-note">Files are private and stay available until Esicom staff deletes them. Uploads are limited to 50 MB. WhatsApp sharing requires the customer to confirm sending.</p><div class="qr-actions"><button class="btn btn-primary" type="button" data-print-qr>Print QR code</button><a class="btn btn-light" data-qr-download download="esicom-file-upload-qr.png">Download QR image</a><a class="btn btn-light" href="/send-file/">Open upload page</a></div></div></div></section></main>'''

def page_html(path,data):
    content=home_content() if data['kind']=='home' else contact_content(data) if data['kind']=='contact' else upload_content() if data['kind']=='upload' else file_qr_content() if data['kind']=='qr' else detail_content(path,data)
    title='Esicom Suppliers | '+('Supply. Print. Brand.' if path=='/' else data['eyebrow'].title())
    desc=esc(data['intro'])
    page_key='home' if path=='/' else path.strip('/')
    content=content.replace('<main>','<main id="main-content" tabindex="-1" data-content-page="'+page_key+'">',1)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="{NAVY}"><meta name="description" content="{desc}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{desc}"><title>{esc(title)}</title><link rel="stylesheet" href="/styles.css?v=4"><script src="/site-config.js?v=3"></script></head><body>{header(path)}{content}{footer()}</body></html>'''

def main():
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST/'styles.css').write_text(CSS,encoding='utf-8')
    (DIST/'site.js').write_text(JS,encoding='utf-8')
    if (ASSETS/'site-config.js').is_file(): shutil.copy2(ASSETS/'site-config.js', DIST/'site-config.js')
    if ASSETS.exists():
        shutil.copytree(ASSETS,DIST,dirs_exist_ok=True)
    api_base=os.environ.get('ESICOM_API_BASE_URL','').strip().rstrip('/')
    if api_base:
        parsed_api_base=urlsplit(api_base)
        if parsed_api_base.scheme!='https' or not parsed_api_base.netloc or parsed_api_base.path not in ('','/') or parsed_api_base.query or parsed_api_base.fragment:
            raise SystemExit('BUILD FAILED: ESICOM_API_BASE_URL must be an HTTPS origin, such as https://esicom-api.onrender.com')
        (DIST/'site-config.js').write_text(
            'window.ESICOM_API_BASE_URL = '+json.dumps(api_base)+';\n',
            encoding='utf-8',
        )
    for path,data in PAGES.items():
        folder=DIST if path=='/' else DIST/path.strip('/')
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(page_html(path,data),encoding='utf-8')
    # Build aliases to preserve service-specific routes from the previous project.
    aliases={'/products/office-supplies/':'/office-supplies/','/products/computer-consumables/':'/computer-consumables/','/products/paper-filing/':'/paper-filing/','/services/printing/':'/bulk-printing/','/services/branding/':'/branding/','/services/business-cards/':'/business-cards/','/services/branded-apparel/':'/branded-apparel/','/services/diaries-asset-tags/':'/diaries-asset-tags/','/products/':'/office-supplies/'}
    for alias,target in aliases.items():
        folder=DIST/alias.strip('/'); folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><link rel="canonical" href="{target}"><title>Continue to Esicom Suppliers</title></head><body><p>This page has moved. <a href="{target}">Continue to the relevant page</a>.</p></body></html>',encoding='utf-8')
    # Build gate: all expected pages, key facts, internal targets and assets must exist.
    required=['index.html','office-supplies/index.html','computer-consumables/index.html','bulk-printing/index.html','branding/index.html','about/index.html','contact/index.html','send-file/index.html','file-qr/index.html','catalogue/esicom-suppliers-catalogue.pdf','images/photography/workspace.webp','images/photography/stationery.webp','images/photography/computer.webp','images/photography/printing.webp','images/photography/apparel.webp','images/photography/meeting-room.webp','images/photography/notebook.webp','images/photography/stock-boxed-pens.webp','images/photography/stock-copy-paper.webp','styles.css','site.js']
    missing=[x for x in required if not (DIST/x).is_file()]
    if missing: raise SystemExit('BUILD FAILED: missing files: '+', '.join(missing))
    bad=['10+ years','500+ clients','same-day delivery','nationwide delivery','SME support','authorized distributor','certifications']
    content='\n'.join(p.read_text(errors='ignore') for p in DIST.rglob('*.html')).lower()
    found=[x for x in bad if x in content]
    if found: raise SystemExit('BUILD FAILED: unsupported claims found: '+', '.join(found))
    if '/images/mockups/' in content or 'images.unsplash.com/' in content:
        raise SystemExit('BUILD FAILED: pages must use local photography assets, not mockups or remote photos')
    for path in PAGES:
        p = DIST/'index.html' if path=='/' else DIST/path.strip('/')/'index.html'
        txt=p.read_text()
        if PAGES[path]['kind']=='upload':
            if any(value not in txt for value in ('data-file-upload-form', '15 MB', '50 MB', 'delivery_consent', 'until Esicom staff deletes them')):
                raise SystemExit('BUILD FAILED: file upload page is missing its delivery options, consent, or stated limits.')
            continue
        if PAGES[path]['kind']=='qr':
            if 'data-upload-qr' not in txt or 'data-print-qr' not in txt:
                raise SystemExit('BUILD FAILED: printable file-upload QR page is incomplete.')
            continue
        if 'esicomsuppliers@gmail.com' not in txt or '0728 942 669' not in txt:
            raise SystemExit(f'BUILD FAILED: contact detail missing from {p.relative_to(DIST)}')
        page_key='home' if path=='/' else path.strip('/')
        if f'data-content-page="{page_key}"' not in txt or 'data-copy-image' not in txt:
            raise SystemExit(f'BUILD FAILED: CMS page or hero-image wiring missing from {p.relative_to(DIST)}')
        if PAGES[path]['kind']=='home' and 'data-featured-products' not in txt:
            raise SystemExit('BUILD FAILED: homepage product listing is not CMS-ready')
        if PAGES[path]['kind']=='detail' and 'data-category-products' not in txt:
            raise SystemExit(f'BUILD FAILED: category product listing is not CMS-ready on {p.relative_to(DIST)}')
    print(f'BUILD OK: {len(list(DIST.rglob("index.html")))} HTML pages, catalogue PDF and locally stored photography written to {DIST}')

if __name__=='__main__': main()
