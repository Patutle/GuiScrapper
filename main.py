import os
import requests
import zipfile
import pdfkit
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import time

# **🔹 Setup Firefox WebDriver *Browers of choice**
firefox_options = Options()
firefox_options.add_argument("--headless")
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=firefox_options)

# **🔹 Fix URL if missing `http://` or `https://`**
def format_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# **🔹 Sanitize Filename **
def sanitize_filename(url):
    parsed_url = urlparse(url)
    filename = parsed_url.netloc.replace(".", "_") + parsed_url.path.replace("/", "_")
    return filename if filename else "index"

# **🔹 Download Static Files**
def download_resource(url, folder):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        response.raise_for_status()

        resource_name = os.path.basename(urlparse(url).path) or "file"
        file_path = os.path.join(folder, resource_name)
        os.makedirs(folder, exist_ok=True)

        with open(file_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)

        return file_path
    except:
        return None

# **🔹 Scrape and Save a Web Page (Runs in Background)**
def scrape_page(url, base_url, output_folder, visited_pages):
    url = format_url(url)
    if url in visited_pages:
        return
    # Wait for JavaScript to load so it keep working
    print(f"🔍 Scraping: {url}")
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # **Download Resources**
    for tag, attr in [("img", "src"), ("script", "src"), ("link", "href")]:
        for resource in soup.find_all(tag):
            if resource.has_attr(attr):
                resource_url = urljoin(url, resource[attr])
                resource_path = download_resource(resource_url, output_folder)
                if resource_path:
                    resource[attr] = os.path.relpath(resource_path, output_folder)

    # **Save HTML File**
    page_filename = "index.html" if url == base_url else sanitize_filename(url) + ".html"
    page_path = os.path.join(output_folder, page_filename)
    with open(page_path, "w", encoding="utf-8") as file:
        file.write(str(soup))

    visited_pages.add(url)
    print(f"✅ Saved: {page_path}")

    # **Update Progress Bar, so you can see how long it takes**
    progress["value"] += 5
    root.update_idletasks()

    # **Find and Download Internal Links**
    for link in soup.find_all("a", href=True):
        full_link = urljoin(url, link["href"])
        if base_url in full_link and full_link not in visited_pages:
            scrape_page(full_link, base_url, output_folder, visited_pages)

# **🔹 Convert HTML to PDF**
def save_as_pdf(output_folder):
    html_file = os.path.join(output_folder, "index.html")
    pdf_path = os.path.join(output_folder, "website.pdf")

    if os.path.exists(html_file):
        pdfkit.from_file(html_file, pdf_path)
        print(f"📄 Website saved as PDF: {pdf_path}")
        return pdf_path
    else:
        print("❌ No HTML file found to convert.")
        return None

# **🔹 Zip the Downloaded Website**
def zip_website(output_folder):
    zip_path = output_folder + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_folder):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_folder))

    print(f"📦 Website zipped: {zip_path}")
    return zip_path

# **🔹 Run Scraper in Background**
def start_scraper():
    website_url = url_entry.get().strip()
    if not website_url:
        messagebox.showerror("Error", "Please enter a website URL.")
        return

    website_url = format_url(website_url)
    base_url = "{0.scheme}://{0.netloc}".format(urlparse(website_url))
    output_folder = sanitize_filename(base_url)
    os.makedirs(output_folder, exist_ok=True)

    visited_pages = set()
    progress["value"] = 0  # Reset progress

    # **Run Scraper in Background**
    threading.Thread(target=scrape_page, args=(website_url, base_url, output_folder, visited_pages)).start()

    # **Process PDF and ZIP in Background**
    if pdf_var.get():
        threading.Thread(target=save_as_pdf, args=(output_folder,)).start()
    if zip_var.get():
        threading.Thread(target=zip_website, args=(output_folder,)).start()

    messagebox.showinfo("Success", "Website download in progress! Check your folder when complete.")

# **🔹 Create GUI**
root = tk.Tk()
root.title("Website Scraper")

tk.Label(root, text="Enter Website URL:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

# **Check buttons for PDF & ZIP options**
pdf_var = tk.BooleanVar()
zip_var = tk.BooleanVar()

pdf_checkbox = tk.Checkbutton(root, text="Save as PDF", variable=pdf_var)
pdf_checkbox.pack()

zip_checkbox = tk.Checkbutton(root, text="Save as ZIP", variable=zip_var)
zip_checkbox.pack()

# **Progress Bar**
progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.pack(pady=10)

# **Scrape Button**
scrape_button = tk.Button(root, text="Download Website", command=start_scraper)
scrape_button.pack(pady=10)

root.mainloop()

# **Quit Selenium**
driver.quit()
