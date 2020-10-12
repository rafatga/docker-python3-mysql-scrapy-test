from flask import Flask
from flask import render_template
from mysql.connector import Error
import mysql.connector
from twisted.internet import reactor
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy import signals

class DBManager:
	def __init__(self, port='3306', database='myblog', host='db', user='foo2020', password='demo'):
		self.connection = mysql.connector.connect(
			user=user, 
			host=host,
			port=port,
			password=password,
			database=database
		)
		self.cursor = self.connection.cursor(buffered=True)

	def getArticles(self):
		sql = 'SELECT a.*, au.name as author_name FROM articles a LEFT JOIN authors au ON au.id = a.author_id'
		self.cursor.execute(sql)
		columns = [column[0] for column in self.cursor.description]
		results = []
		for article in self.cursor.fetchall():
			articleDic = dict(zip(columns, article))
			articleDic['tags'] = self.getArticleTags(articleDic['id'])
			results.append(articleDic)
		return results

	def getAuthorByName(self, name):
		sql = 'SELECT au.* FROM authors au WHERE au.name = "%s"'
		self.cursor.execute(sql, (name,))
		self.connection.commit()
		return self.cursor.fetchone()

	def getTagByName(self, name):
		sql = 'SELECT t.* FROM tags t WHERE t.name = "%s"'
		self.cursor.execute(sql, (name,))
		self.connection.commit()
		return self.cursor.fetchone()	

	def getArticleTags(self, article):
		sql = 'SELECT t.* FROM tags t LEFT JOIN articles_tags at ON at.tag_id = t.id WHERE at.article_id = %s'
		self.cursor.execute(sql, (article,))
		columns = [column[0] for column in self.cursor.description]
		results = []
		for row in self.cursor.fetchall():
			results.append(dict(zip(columns, row)))
		return results	

	def addAuthor(self, name):
		sql = 'INSERT INTO authors(name) VALUES (%s)'
		self.cursor.execute(sql, (name,))
		self.connection.commit()
		return { 'id' : self.cursor.lastrowid, 'name' : name }

	def addArticle(self, author, title, body):
		sql = 'INSERT INTO articles(author_id, title, body) VALUES (%s, %s, %s)'
		self.cursor.execute(sql, (author, title, body,))
		self.connection.commit()
		return { 'id' : self.cursor.lastrowid, 'author_id' : author, 'title' : title, 'body' : body }

	def addTag(self, name):
		sql = 'INSERT INTO tags(name) VALUES (%s)'
		self.cursor.execute(sql, (name,))
		self.connection.commit()
		return { 'id' : self.cursor.lastrowid, 'name' : name }

	def addArticleTag(self, article, tagName):
		tag = self.getTagByName(tagName)
		if( tag == None):
			tag = self.addTag(tagName)
		sql = 'INSERT INTO articles_tags(article_id, tag_id) VALUES (%s, %s)'
		self.cursor.execute(sql, (article, tag['id'],))
		self.connection.commit()
		return { 'id' : self.cursor.lastrowid, 'article_id' : article, 'tag_id' : tag['id'],  'tagName' : tagName }	

# My custom scrapy object extends from scrapy.Spider
class DevToSpider(scrapy.Spider):
	name = 'mycustomspider'
	custom_settings = { 'DOWNLOD_DELAY': 0, 'LOG_LEVEL': 'ERROR', 'LOG_ENABLED': False, 'SCHEDULER_DEBUG': False }
	start_urls = ['http://quotes.toscrape.com/page/1/']
	headers = {}
	params = {}

	def parse(self,response):
		global conn
		for quote in response.css('div.quote'):
			newAuthorName = quote.css('.author::text').extract_first()
			author = conn.getAuthorByName(newAuthorName)
			if author == None:
				author = conn.addAuthor(newAuthorName)
			body = quote.css('.text::text').extract_first()
			title = (body[:75] + '..') if len(body) > 75 else body
			article = conn.addArticle( author['id'], title, body)
			for tagName in quote.css('div.tags > a.tag::text').getall():
				conn.addArticleTag(article['id'], tagName)
				

app = Flask(__name__)
conn = None

# Home page
@app.route("/")
def home():
	global conn
	if not conn:
		conn = DBManager()
	data = {
		'articles': conn.getArticles()
	}
	return render_template('home.html', data=data)

# Extract information from website and save it in database
@app.route("/start/spiders")
def start_spiders():
	global conn
	if not conn:
		conn = DBManager()
	crawlerRunner = CrawlerRunner()
	crawlerRunner.crawl(DevToSpider)
	d = crawlerRunner.join()
	d.addBoth(lambda _: reactor.stop())
	#dispatcher.connect(add_item, signal=signals.item_passed)
	reactor.run()
	return "SCRAPING"

def add_item(item):
	crawle = 'done'

# Starts de application
if __name__ == "__main__":
	# Only for debugging while developing
	app.run(host="0.0.0.0", debug=True, port=80)