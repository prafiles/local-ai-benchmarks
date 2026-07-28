#!/usr/bin/env python3
"""Django category — 50 ORM tasks against a real database.

Query-count assertions (CaptureQueriesContext) make N+1 and bulk-operation
tasks objectively checkable rather than pattern-matched.
"""

MODELS = """
from django.db import models

class Publisher(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)

class Author(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)
    born = models.IntegerField()

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name='books')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    published = models.DateField()
    pages = models.IntegerField()
    genre = models.CharField(max_length=20)

class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    body = models.TextField()
"""

CTX = ("Given these Django models:\n\n```python\n" + MODELS.strip() + "\n```\n\n"
       "Publisher, Author, Book and Review are already imported, as are django.db.models "
       "helpers you may need (import anything else you use).\n\n")

SEED = """
p1 = Publisher.objects.create(name='Acme', country='UK')
p2 = Publisher.objects.create(name='Bolt', country='US')
ann = Author.objects.create(name='Ann', country='UK', born=1970)
bob = Author.objects.create(name='Bob', country='US', born=1980)
cid = Author.objects.create(name='Cid', country='UK', born=1990)
dee = Author.objects.create(name='Dee', country='DE', born=1975)   # no books
import datetime as _dt
b1 = Book.objects.create(title='B1', author=ann, publisher=p1, price=10,
                         published=_dt.date(2021,1,1), pages=100, genre='sci')
b2 = Book.objects.create(title='B2', author=ann, publisher=p1, price=20,
                         published=_dt.date(2022,6,1), pages=200, genre='sci')
b3 = Book.objects.create(title='B3', author=bob, publisher=p2, price=30,
                         published=_dt.date(2023,3,1), pages=300, genre='lit')
b4 = Book.objects.create(title='B4', author=bob, publisher=p1, price=40,
                         published=_dt.date(2024,5,1), pages=150, genre='lit')
b5 = Book.objects.create(title='C5', author=cid, publisher=p2, price=50,
                         published=_dt.date(2020,2,1), pages=250, genre='sci')
for bk, ratings in ((b1,[5,3]), (b2,[4]), (b3,[2]), (b5,[5,5,1])):
    for r in ratings:
        Review.objects.create(book=bk, rating=r, body='x')
"""

# (id, spec, tests, reference)
T = [
("dj-001", "function `prolific(n)` returning a QuerySet of Authors with strictly more than n books, "
 "annotated with `book_count`, ordered by book_count descending then name.",
 "r=list(prolific(1))\nassert [a.name for a in r]==['Ann','Bob'], [a.name for a in r]\n"
 "assert r[0].book_count==2\nassert list(prolific(5))==[]",
 "from django.db.models import Count\n"
 "def prolific(n):\n"
 "    return Author.objects.annotate(book_count=Count('books')).filter(book_count__gt=n)"
 ".order_by('-book_count','name')"),
("dj-002", "function `books_with_authors()` returning a QuerySet of all Books that will not trigger "
 "an extra query per book when accessing book.author.name.",
 "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
 "with CaptureQueriesContext(connection) as c:\n"
 "    for b in books_with_authors(): _=b.author.name\n"
 "assert len(c.captured_queries)==1, len(c.captured_queries)",
 "def books_with_authors():\n    return Book.objects.select_related('author')"),
("dj-003", "function `price_stats()` returning a dict with keys 'total' and 'avg' over all Book "
 "prices, computed in a single database aggregate query.",
 "from decimal import Decimal\ns=price_stats()\n"
 "assert round(Decimal(str(s['total'])),2)==Decimal('150.00'), s\n"
 "assert round(Decimal(str(s['avg'])),2)==Decimal('30.00'), s",
 "from django.db.models import Sum, Avg\n"
 "def price_stats():\n"
 "    r=Book.objects.aggregate(total=Sum('price'), avg=Avg('price'))\n"
 "    return {'total': r['total'], 'avg': r['avg']}"),
("dj-004", "function `by_author_substring(sub)` returning Books whose author's name contains sub "
 "case-insensitively, ordered by published ascending.",
 "assert [b.title for b in by_author_substring('an')]==['B1','B2']\n"
 "assert list(by_author_substring('zzz'))==[]",
 "def by_author_substring(sub):\n"
 "    return Book.objects.filter(author__name__icontains=sub).order_by('published')"),
("dj-005", "function `add_books(author, publisher, titles, price, when)` creating one Book per title "
 "in a single INSERT statement, returning the number created. Use pages=1 and genre='x'.",
 "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
 "import datetime\na=Author.objects.get(name='Ann'); p=Publisher.objects.get(name='Acme')\n"
 "with CaptureQueriesContext(connection) as c:\n"
 "    n=add_books(a,p,['X','Y','Z'],5,datetime.date(2024,1,1))\n"
 "assert n==3, n\n"
 "ins=[q for q in c.captured_queries if 'INSERT' in q['sql'].upper()]\n"
 "assert len(ins)==1, len(ins)",
 "def add_books(author, publisher, titles, price, when):\n"
 "    objs=[Book(title=t, author=author, publisher=publisher, price=price,\n"
 "               published=when, pages=1, genre='x') for t in titles]\n"
 "    return len(Book.objects.bulk_create(objs))"),
("dj-006", "function `cheaper_than(x)` returning Books priced strictly below x ordered by price ascending.",
 "assert [b.title for b in cheaper_than(30)]==['B1','B2']\nassert list(cheaper_than(1))==[]",
 "def cheaper_than(x):\n    return Book.objects.filter(price__lt=x).order_by('price')"),
("dj-007", "function `authors_without_books()` returning Authors having no books, ordered by name.",
 "assert [a.name for a in authors_without_books()]==['Dee']",
 "def authors_without_books():\n    return Author.objects.filter(books__isnull=True).order_by('name')"),
("dj-008", "function `genre_counts()` returning a list of dicts with keys 'genre' and 'n' counting "
 "books per genre, ordered by genre.",
 "assert list(genre_counts())==[{'genre':'lit','n':2},{'genre':'sci','n':3}]",
 "from django.db.models import Count\n"
 "def genre_counts():\n"
 "    return list(Book.objects.values('genre').annotate(n=Count('id')).order_by('genre'))"),
("dj-009", "function `published_between(a, b)` returning Books published between two dates inclusive, "
 "ordered by published.",
 "import datetime\n"
 "r=[x.title for x in published_between(datetime.date(2021,1,1),datetime.date(2023,1,1))]\n"
 "assert r==['B1','B2'], r",
 "def published_between(a,b):\n"
 "    return Book.objects.filter(published__gte=a, published__lte=b).order_by('published')"),
("dj-010", "function `all_genres()` returning a sorted list of the distinct genre strings.",
 "assert all_genres()==['lit','sci']",
 "def all_genres():\n"
 "    return sorted(Book.objects.values_list('genre', flat=True).distinct())"),
("dj-011", "function `books_with_reviews()` returning Books such that iterating them and reading "
 "list(book.reviews.all()) issues only 2 queries in total.",
 "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
 "with CaptureQueriesContext(connection) as c:\n"
 "    for b in books_with_reviews(): _=list(b.reviews.all())\n"
 "assert len(c.captured_queries)==2, len(c.captured_queries)",
 "def books_with_reviews():\n    return Book.objects.prefetch_related('reviews')"),
("dj-012", "function `avg_rating_per_book()` returning a list of dicts with 'title' and 'avg_rating' "
 "for books that have reviews, ordered by title.",
 "r=avg_rating_per_book()\nassert r[0]['title']=='B1' and abs(float(r[0]['avg_rating'])-4.0)<1e-6\n"
 "assert len(r)==4, r",
 "from django.db.models import Avg\n"
 "def avg_rating_per_book():\n"
 "    return list(Book.objects.filter(reviews__isnull=False).values('title')"
 ".annotate(avg_rating=Avg('reviews__rating')).order_by('title'))"),
("dj-013", "function `unreviewed()` returning Books with no reviews, ordered by title.",
 "assert [b.title for b in unreviewed()]==['B4']",
 "def unreviewed():\n    return Book.objects.filter(reviews__isnull=True).order_by('title')"),
("dj-014", "function `raise_prices(pct)` increasing every Book price by pct percent using a database "
 "expression in a single UPDATE, returning the number of rows affected.",
 "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
 "with CaptureQueriesContext(connection) as c:\n    n=raise_prices(10)\n"
 "assert n==5, n\n"
 "ups=[q for q in c.captured_queries if 'UPDATE' in q['sql'].upper()]\n"
 "assert len(ups)==1, len(ups)\n"
 "from decimal import Decimal\n"
 "assert Book.objects.get(title='B1').price==Decimal('11.00')",
 "from django.db.models import F\n"
 "def raise_prices(pct):\n"
 "    return Book.objects.update(price=F('price')*(1+pct/100.0))"),
("dj-015", "function `purge_cheap(x)` deleting Books priced below x and returning how many Book rows "
 "were deleted.",
 "assert purge_cheap(25)==2\nassert Book.objects.count()==3",
 "def purge_cheap(x):\n"
 "    n,_d=Book.objects.filter(price__lt=x).delete()\n"
 "    return _d.get('__main__.Book', _d.get('bench_app.Book', n))"),
("dj-016", "function `ensure_author(name, country, born)` returning a tuple (author, created) that "
 "fetches an existing Author by name or creates one.",
 "a,c=ensure_author('Ann','UK',1970)\nassert c is False and a.name=='Ann'\n"
 "b,c2=ensure_author('Zed','NZ',2000)\nassert c2 is True and Author.objects.filter(name='Zed').exists()",
 "def ensure_author(name,country,born):\n"
 "    return Author.objects.get_or_create(name=name, defaults={'country':country,'born':born})"),
("dj-017", "function `longest(n)` returning the n Books with the most pages, ordered by pages descending.",
 "assert [b.title for b in longest(2)]==['B3','C5']",
 "def longest(n):\n    return Book.objects.order_by('-pages')[:n]"),
("dj-018", "function `authors_from(country)` returning Authors from that country ordered by name.",
 "assert [a.name for a in authors_from('UK')]==['Ann','Cid']",
 "def authors_from(country):\n    return Author.objects.filter(country=country).order_by('name')"),
("dj-019", "function `cheap_or_long(price, pages)` returning Books priced below price OR having more "
 "pages than pages, ordered by title, using a Q expression.",
 "r=[b.title for b in cheap_or_long(15,250)]\nassert r==['B1','B3'], r",
 "from django.db.models import Q\n"
 "def cheap_or_long(price,pages):\n"
 "    return Book.objects.filter(Q(price__lt=price)|Q(pages__gt=pages)).order_by('title')"),
("dj-020", "function `not_genre(g)` returning Books whose genre is not g, ordered by title.",
 "assert [b.title for b in not_genre('sci')]==['B3','B4']",
 "def not_genre(g):\n    return Book.objects.exclude(genre=g).order_by('title')"),
("dj-021", "function `has_expensive(x)` returning True if any Book costs more than x, using a query "
 "that does not fetch the rows.",
 "assert has_expensive(45) is True and has_expensive(500) is False",
 "def has_expensive(x):\n    return Book.objects.filter(price__gt=x).exists()"),
("dj-022", "function `titles()` returning a flat list of all Book titles ordered by title.",
 "assert titles()==['B1','B2','B3','B4','C5']",
 "def titles():\n    return list(Book.objects.order_by('title').values_list('title', flat=True))"),
("dj-023", "function `rating_totals()` returning a list of dicts with 'title' and 'total' summing the "
 "review ratings per book, only for reviewed books, ordered by title.",
 "r=rating_totals()\nassert r[0]=={'title':'B1','total':8}, r[0]\nassert len(r)==4",
 "from django.db.models import Sum\n"
 "def rating_totals():\n"
 "    return list(Book.objects.filter(reviews__isnull=False).values('title')"
 ".annotate(total=Sum('reviews__rating')).order_by('title'))"),
("dj-024", "function `by_publisher(name)` returning Books whose publisher has that name, ordered by title.",
 "assert [b.title for b in by_publisher('Acme')]==['B1','B2','B4']",
 "def by_publisher(name):\n"
 "    return Book.objects.filter(publisher__name=name).order_by('title')"),
("dj-025", "function `first_and_last()` returning a tuple of the earliest and latest Book by published date.",
 "a,b=first_and_last()\nassert a.title=='C5' and b.title=='B4'",
 "def first_and_last():\n"
 "    return Book.objects.earliest('published'), Book.objects.latest('published')"),
("dj-026", "function `authors_in_genre(g)` returning the number of distinct authors having at least one "
 "book in genre g.",
 "assert authors_in_genre('sci')==2 and authors_in_genre('lit')==1",
 "def authors_in_genre(g):\n"
 "    return Author.objects.filter(books__genre=g).distinct().count()"),
("dj-027", "function `titled(prefix)` returning Books whose title starts with prefix, ordered by title.",
 "assert [b.title for b in titled('B')]==['B1','B2','B3','B4']",
 "def titled(prefix):\n    return Book.objects.filter(title__startswith=prefix).order_by('title')"),
("dj-028", "function `price_range()` returning a dict with keys 'lo' and 'hi' for the min and max Book price.",
 "from decimal import Decimal\nr=price_range()\n"
 "assert Decimal(str(r['lo']))==Decimal('10') and Decimal(str(r['hi']))==Decimal('50')",
 "from django.db.models import Min, Max\n"
 "def price_range():\n"
 "    r=Book.objects.aggregate(lo=Min('price'), hi=Max('price'))\n"
 "    return {'lo': r['lo'], 'hi': r['hi']}"),
("dj-029", "function `publisher_revenue()` returning a list of dicts with 'name' and 'total' summing "
 "book prices per publisher, ordered by name.",
 "from decimal import Decimal\nr=publisher_revenue()\n"
 "assert r[0]['name']=='Acme' and Decimal(str(r[0]['total']))==Decimal('70')\n"
 "assert r[1]['name']=='Bolt' and Decimal(str(r[1]['total']))==Decimal('80')",
 "from django.db.models import Sum\n"
 "def publisher_revenue():\n"
 "    return list(Publisher.objects.values(name=F('name')).annotate(total=Sum('books__price'))"
 ".order_by('name')) if False else list(Publisher.objects.annotate(total=Sum('books__price'))"
 ".order_by('name').values('name','total'))"),
("dj-030", "function `well_reviewed(x)` returning Books whose average review rating is at least x, "
 "ordered by title.",
 "assert [b.title for b in well_reviewed(4)]==['B1','B2']",
 "from django.db.models import Avg\n"
 "def well_reviewed(x):\n"
 "    return Book.objects.annotate(a=Avg('reviews__rating')).filter(a__gte=x).order_by('title')"),
("dj-031", "function `by_author_then_title()` returning all Books ordered by author name then title.",
 "assert [b.title for b in by_author_then_title()]==['B1','B2','B3','B4','C5']",
 "def by_author_then_title():\n    return Book.objects.order_by('author__name','title')"),
("dj-032", "function `titles_only()` returning a QuerySet of Books that loads only the id and title "
 "columns from the database.",
 "qs=titles_only()\nq=str(qs.query).lower()\n"
 "assert 'price' not in q and 'title' in q, q",
 "def titles_only():\n    return Book.objects.only('title')"),
("dj-033", "function `sci_counts()` returning a list of dicts with 'name' and 'n' per author, where n "
 "counts only their sci-genre books, ordered by name.",
 "r=sci_counts()\nd={x['name']:x['n'] for x in r}\n"
 "assert d['Ann']==2 and d['Bob']==0 and d['Cid']==1 and d['Dee']==0, d",
 "from django.db.models import Count, Q\n"
 "def sci_counts():\n"
 "    return list(Author.objects.annotate(n=Count('books', filter=Q(books__genre='sci')))"
 ".order_by('name').values('name','n'))"),
("dj-034", "function `newer_than_avg()` returning Books whose pages exceed the average pages across "
 "all books, ordered by title.",
 "r=[b.title for b in newer_than_avg()]\nassert r==['B3','C5'], r",
 "from django.db.models import Avg\n"
 "def newer_than_avg():\n"
 "    a=Book.objects.aggregate(x=Avg('pages'))['x']\n"
 "    return Book.objects.filter(pages__gt=a).order_by('title')"),
("dj-035", "function `by_ids(ids)` returning Books whose primary key is in the given list, ordered by title.",
 "ids=list(Book.objects.order_by('title').values_list('id',flat=True))[:2]\n"
 "assert [b.title for b in by_ids(ids)]==['B1','B2']",
 "def by_ids(ids):\n    return Book.objects.filter(pk__in=ids).order_by('title')"),
("dj-036", "function `published_in(year)` returning Books published in that calendar year, ordered by title.",
 "assert [b.title for b in published_in(2021)]==['B1']\nassert list(published_in(1999))==[]",
 "def published_in(year):\n"
 "    return Book.objects.filter(published__year=year).order_by('title')"),
("dj-037", "function `rename_book(old, new)` changing the title of the Book titled old to new and "
 "returning the saved instance.",
 "b=rename_book('B1','Renamed')\nassert b.title=='Renamed'\n"
 "assert Book.objects.filter(title='Renamed').count()==1",
 "def rename_book(old,new):\n"
 "    b=Book.objects.get(title=old); b.title=new; b.save(); return b"),
("dj-038", "function `add_review(title, rating)` creating a Review with body 'ok' for the Book with "
 "that title and returning it.",
 "r=add_review('B4',5)\nassert r.rating==5 and r.book.title=='B4'\n"
 "assert Book.objects.get(title='B4').reviews.count()==1",
 "def add_review(title,rating):\n"
 "    return Review.objects.create(book=Book.objects.get(title=title), rating=rating, body='ok')"),
("dj-039", "function `full_books()` returning Books such that reading book.author.name and "
 "book.publisher.name for every book costs exactly one query in total.",
 "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
 "with CaptureQueriesContext(connection) as c:\n"
 "    for b in full_books(): _=b.author.name; _=b.publisher.name\n"
 "assert len(c.captured_queries)==1, len(c.captured_queries)",
 "def full_books():\n    return Book.objects.select_related('author','publisher')"),
("dj-040", "function `avg_pages()` returning the average pages across all Books as a float.",
 "assert abs(avg_pages()-200.0)<1e-6, avg_pages()",
 "from django.db.models import Avg\n"
 "def avg_pages():\n    return float(Book.objects.aggregate(a=Avg('pages'))['a'])"),
("dj-041", "function `priced_between(lo, hi)` returning Books with price between lo and hi inclusive, "
 "ordered by price.",
 "assert [b.title for b in priced_between(20,40)]==['B2','B3','B4']",
 "def priced_between(lo,hi):\n"
 "    return Book.objects.filter(price__range=(lo,hi)).order_by('price')"),
("dj-042", "function `price_per_page()` returning a list of dicts with 'title' and 'ppp' computed in "
 "the database as price divided by pages, ordered by title. It must be a true floating-point "
 "division (a plain integer division would round to zero on SQLite).",
 "r=price_per_page()\nassert abs(float(r[0]['ppp'])-0.1)<1e-6, r[0]",
 "from django.db.models import F, FloatField, ExpressionWrapper\n"
 "def price_per_page():\n"
 "    return list(Book.objects.annotate(ppp=ExpressionWrapper(F('price')*1.0/F('pages'),"
 "output_field=FloatField())).order_by('title').values('title','ppp'))"),
("dj-043", "function `authors_of_genre(g)` returning Authors who wrote at least one book of genre g, "
 "without duplicates, ordered by name.",
 "assert [a.name for a in authors_of_genre('sci')]==['Ann','Cid']",
 "def authors_of_genre(g):\n"
 "    return Author.objects.filter(books__genre=g).distinct().order_by('name')"),
("dj-044", "function `countries_with_books()` returning a sorted list of distinct author countries that "
 "have at least one book.",
 "assert countries_with_books()==['UK','US']",
 "def countries_with_books():\n"
 "    return sorted(set(Author.objects.filter(books__isnull=False)"
 ".values_list('country', flat=True)))"),
("dj-045", "function `review_counts()` returning a list of dicts with 'name' and 'n' counting distinct "
 "reviews across each author's books, ordered by name.",
 "d={x['name']:x['n'] for x in review_counts()}\n"
 "assert d['Ann']==3 and d['Bob']==1 and d['Cid']==3 and d['Dee']==0, d",
 "from django.db.models import Count\n"
 "def review_counts():\n"
 "    return list(Author.objects.annotate(n=Count('books__reviews', distinct=True))"
 ".order_by('name').values('name','n'))"),
("dj-046", "function `price_band()` returning a list of dicts with 'title' and 'band', where band is "
 "'cheap' when price is below 25 and 'dear' otherwise, computed in the database, ordered by title.",
 "d={x['title']:x['band'] for x in price_band()}\n"
 "assert d['B1']=='cheap' and d['B4']=='dear', d",
 "from django.db.models import Case, When, Value, CharField\n"
 "def price_band():\n"
 "    return list(Book.objects.annotate(band=Case(When(price__lt=25, then=Value('cheap')),"
 "default=Value('dear'), output_field=CharField())).order_by('title').values('title','band'))"),
("dj-047", "function `safe_avg_rating()` returning a list of dicts with 'title' and 'avg_rating' for "
 "every book, using 0 instead of None for books with no reviews, ordered by title.",
 "d={x['title']:float(x['avg_rating']) for x in safe_avg_rating()}\n"
 "assert abs(d['B4']-0.0)<1e-6 and abs(d['B1']-4.0)<1e-6, d",
 "from django.db.models import Avg, Value, FloatField\n"
 "from django.db.models.functions import Coalesce\n"
 "def safe_avg_rating():\n"
 "    return list(Book.objects.annotate(avg_rating=Coalesce(Avg('reviews__rating'),"
 "Value(0.0), output_field=FloatField())).order_by('title').values('title','avg_rating'))"),
("dj-048", "function `bump_pages(n)` adding n to the pages of every Book using bulk_update, returning "
 "the number of books updated.",
 "assert bump_pages(5)==5\nassert Book.objects.get(title='B1').pages==105",
 "def bump_pages(n):\n"
 "    bs=list(Book.objects.all())\n"
 "    for b in bs: b.pages+=n\n"
 "    Book.objects.bulk_update(bs,['pages'])\n"
 "    return len(bs)"),
("dj-049", "function `book_dicts()` returning a list of dicts with only the 'title' and 'genre' keys "
 "for all books, ordered by title.",
 "r=book_dicts()\nassert r[0]=={'title':'B1','genre':'sci'}, r[0]\nassert len(r)==5",
 "def book_dicts():\n    return list(Book.objects.order_by('title').values('title','genre'))"),
("dj-050", "function `count_books_by(author_name)` returning how many books that author wrote, using a "
 "single COUNT query.",
 "assert count_books_by('Ann')==2 and count_books_by('Dee')==0",
 "def count_books_by(author_name):\n"
 "    return Book.objects.filter(author__name=author_name).count()"),
]

HARNESS = """
import django, datetime
from django.conf import settings
settings.configure(DEBUG=True, USE_TZ=True,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    INSTALLED_APPS=["bench_app"], DEFAULT_AUTO_FIELD="django.db.models.BigAutoField")
django.setup()
from django.db import connection
from bench_app.models import Publisher, Author, Book, Review
from django.db.models import F
with connection.schema_editor() as se:
    for m in (Publisher, Author, Book, Review):
        se.create_model(m)
exec(open("/w/seed.py").read(), globals())
exec(open("/w/sol.py").read(), globals())
exec(open("/w/test.py").read(), globals())
print("OK")
"""


def tasks():
    return [(tid, CTX + "Write a " + spec + "\n\nOutput only the code, no explanation.", tests)
            for tid, spec, tests, _r in T]


if __name__ == "__main__":
    ids = [t[0] for t in T]
    assert len(ids) == len(set(ids))
    print(f"django tasks: {len(T)}  ids unique: ok")
