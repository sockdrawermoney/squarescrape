import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import html2text
import re
import time
import datetime
import string

# modify these based on your needs
blog_url = "https://yoursite.com/blog"
post_class = "post"
title_class = "entry-title"
date_class = "published"
categories_class = "categories"
body_class = "entry-content"

# conservatively avoid squarespace's 300 requests/min cap
MAX_REQUESTS_PER_MINUTE = 150

def download_image(image_url, folder):
	os.makedirs(folder, exist_ok=True)
	filename = os.path.basename(urlparse(image_url).path)
	filepath = os.path.join(folder, filename)
	with requests.get(image_url, stream=True) as r:
			r.raise_for_status()
			with open(filepath, 'wb') as f:
					for chunk in r.iter_content(chunk_size=8192):
							f.write(chunk)
	print('Downloaded image: {}'.format(filename))

def process_post(post_url, post_class, title_class, date_class, categories_class, body_class):
		response = requests.get(post_url)
		if response.status_code == 429:
				print('\033[91mReceived 429 response for: {}\033[0m'.format(post_url))
				time.sleep(60)
				process_post(post_url, post_class, title_class, date_class, categories_class, body_class)
				return
		soup = BeautifulSoup(response.text, 'html.parser')
		post_div = soup.find('div', {'class': post_class})
		title = soup.find('h1', {'class': title_class}).get_text()
		date_str = soup.find('time', {'class': date_class})['datetime']
		date = datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d')
		tags_div = soup.find('div', {'class': categories_class})
		tags = []
		if tags_div:
			tags = tags_div.get_text().strip().lower().split()
			tags = [tag.translate(str.maketrans('', '', string.punctuation)) for tag in tags]
			tags = [tag.replace(' ', '-') for tag in tags]
		html_content = str(soup.find('div', {'class': body_class}))
		image_links = post_div.find_all('img', src=True)
		for link in image_links:
				full_link = urljoin(post_url, link['src'])
				filename = os.path.basename(urlparse(full_link).path)
				new_link = '/images/{}'.format(filename)
				download_image(full_link, 'images')
				html_content = html_content.replace(str(link), '![{}]({})'.format(filename, new_link))
		h = html2text.HTML2Text()
		h.body_width = 0
		markdown_content = h.handle(html_content)
		filename = os.path.basename(urlparse(post_url).path)
		folder = os.path.join('blog', date[:4])
		os.makedirs(folder, exist_ok=True)
		filepath = os.path.join(folder, '{}.md'.format(filename))
		with open(filepath, 'w') as f:
				f.write('---\n')
				f.write('title: "{}"\n'.format(title))
				f.write('date: "{}"\n'.format(date))
				f.write('tags: [{}]\n'.format(', '.join(['"{}"'.format(tag) for tag in tags])))
				f.write('---\n\n{}'.format(markdown_content))
		print('Processed post: {}'.format(post_url))

def process_blog():
		response = requests.get(blog_url)
		soup = BeautifulSoup(response.text, 'html.parser')
		post_links = soup.select('a[href^="/blog/"]:not([href*="?"])')
		unique_links = set(link.get('href') for link in post_links)
		num_requests = 0
		for link in unique_links:
			post_url = urljoin(blog_url, link)
			process_post(post_url, post_class, title_class, date_class, categories_class, body_class)
			num_requests += 1
			if num_requests >= MAX_REQUESTS_PER_MINUTE:
					num_requests = 0
					time.sleep(60)
		
if __name__ == '__main__':
	process_blog()
