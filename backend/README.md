collins-english-thesaurus web-scraper
operates via docker on ubuntu
consists of the following:
* 2 redis queue containers ( 1 only active at start )
* 1 mongodb container
* 5 scraper containers
using docker, multiple containers are setup that allow for the etraction of lemmas from the collins online thesaurus,
step 1. build containers
step 2. start redis, mongodb containers
  - initially empty
  - storage done persistently with docker volumes
step 3. run load_proxy container
  - this provides the proxies for the scraper containers
step 4. run the scraper containers
  - without any words in the redis queue, these will stay on standby listening to queue
step 5. add word to redis queue ( word_queue )
  - this starts the scraper system as with each page scraped more words will be added to the queue
  - once a word is added, workers will begin processing by popping proxy queue, then pop word_queue from redis
  - using proy, load page for word and scrape foe each lemma found
  - for each lemma found, create a document and add to the mongodb
  - the worker will push any new words found in the synonyms array to the redis word_queue for later processing, allowing this system to run iteratively on its own
  * caveat - this system assumes that all words in collins-online-thesaurus are linked together via their synonyms which is unfortunately not the case
  * as of now, 37,000 lemma have been processed and the queue is empty, collins estimates approximately 170,000 words alone ( there could be up to 7x more lemma than words )

documents stored in mongodb follow this structure:
{
  "_id": {
    "$oid": "6890af9c82f836005c903e18"
  },
  "term": "word",
  "part_of_speech": "noun",
  "definition": "the smallest single meaningful unit of speech or writing",
  "synonyms": [
    "term",
    "name",
    "expression",
    "designation",
    "appellation",
    "locution",
    "vocable"
  ]
}


by this point, the system can be left alone, it will iteratively scrape the collins-online-thesaurus for each lemma found per page, once the queue is emtpy, a new word can be added however it could be difficult to find which words have not already been processed.

'docker ps' - List running containers / See what’s up and which ports are mapped
'docker compose ps' - Inspect Compose services / Shows status from compose perspective
'docker logs -f <container>' - View logs / Follow logs for any container
'docker exec -it <container> sh' - Run a one-off command / Drop into container shell
'docker exec -it api sh -lc 'curl -sS http://localhost:3001/ping'' - Test API inside container / Confirms app is serving internally
'curl -s http://localhost:3001/ping' - Test API from host / Confirms port mapping is working
'curl -s -D- https://api.word-graph.net/ping' - Test API through Cloudflare / head
'docker exec -it api sh -lc ’ss -ltnp' - Check ports inside container / grep 3001
'docker inspect –format ‘{{json .State.Health}}’ api' - Inspect container health / jq
