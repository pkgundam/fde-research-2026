# Data sources used in the FDE Skills Roadmap

All postings were collected from public job-board APIs between 2026-09-14 and 2026-09-15; the report uses the 276 postings first published in the 12 months before collection. No LinkedIn or Indeed data was used.

## Job-board APIs (public, no credentials)

| Source | Endpoint pattern | Postings in report |
|---|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | 83 |
| Lever | `https://api.lever.co/v0/postings/{slug}?mode=json` | 8 |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{slug}` | 111 |
| Hacker News "Who is hiring?" (Algolia) | `https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_<thread id>` | 67 |
| Remotive | `https://remotive.com/api/remote-jobs?search=forward%20deployed` | 0 |
| Arbeitnow | `https://www.arbeitnow.com/api/job-board-api?page=<n>` | 7 |

## Company ATS boards (86 of 230 resolved boards contributed at least one posting)

Boards are listed with the number of postings that made it into the final report after title filtering, de-duplication and the 12-month window. The remaining resolved boards were fetched but had no matching FDE posting at collection time; the full list is in `sources/companies.yaml`.

| Company | ATS | Board | Postings |
|---|---|---|---|
| OpenAI | ashby | https://jobs.ashbyhq.com/openai | 21 |
| Databricks | greenhouse | https://boards.greenhouse.io/databricks | 10 |
| Scale AI | greenhouse | https://boards.greenhouse.io/scaleai | 7 |
| CoreWeave | greenhouse | https://boards.greenhouse.io/coreweave | 6 |
| Handshake AI | ashby | https://jobs.ashbyhq.com/handshake | 6 |
| Snowflake | ashby | https://jobs.ashbyhq.com/snowflake | 6 |
| Anthropic | greenhouse | https://boards.greenhouse.io/anthropic | 5 |
| Cohere | ashby | https://jobs.ashbyhq.com/cohere | 5 |
| Cursor | ashby | https://jobs.ashbyhq.com/cursor | 5 |
| Palantir | lever | https://jobs.lever.co/palantir | 5 |
| Ramp | ashby | https://jobs.ashbyhq.com/ramp | 5 |
| Anduril | greenhouse | https://boards.greenhouse.io/andurilindustries | 4 |
| Cloudflare | greenhouse | https://boards.greenhouse.io/cloudflare | 4 |
| MongoDB | greenhouse | https://boards.greenhouse.io/mongodb | 4 |
| Retell AI | ashby | https://jobs.ashbyhq.com/retell-ai | 4 |
| Snorkel AI | greenhouse | https://boards.greenhouse.io/snorkelai | 4 |
| Composio | ashby | https://jobs.ashbyhq.com/composio | 3 |
| Deepgram | ashby | https://jobs.ashbyhq.com/deepgram | 3 |
| Modal | ashby | https://jobs.ashbyhq.com/modal | 3 |
| Tribe AI | ashby | https://jobs.ashbyhq.com/tribe-ai | 3 |
| UiPath | ashby | https://jobs.ashbyhq.com/uipath | 3 |
| Datadog | greenhouse | https://boards.greenhouse.io/datadog | 2 |
| Decagon | ashby | https://jobs.ashbyhq.com/decagon | 2 |
| Dexterity | lever | https://jobs.lever.co/dexterity | 2 |
| Domino Data Lab | greenhouse | https://boards.greenhouse.io/dominodatalab | 2 |
| ElevenLabs | ashby | https://jobs.ashbyhq.com/elevenlabs | 2 |
| Fireworks AI | ashby | https://jobs.ashbyhq.com/fireworks | 2 |
| GitLab | greenhouse | https://boards.greenhouse.io/gitlab | 2 |
| Intercom | greenhouse | https://boards.greenhouse.io/intercom | 2 |
| Labelbox | greenhouse | https://boards.greenhouse.io/labelbox | 2 |
| Notion | ashby | https://jobs.ashbyhq.com/notion | 2 |
| Okta | greenhouse | https://boards.greenhouse.io/okta | 2 |
| Parloa | greenhouse | https://boards.greenhouse.io/parloa | 2 |
| Reducto | ashby | https://jobs.ashbyhq.com/reducto | 2 |
| SambaNova | greenhouse | https://boards.greenhouse.io/sambanovasystems | 2 |
| Sardine | ashby | https://jobs.ashbyhq.com/sardine | 2 |
| Saronic | ashby | https://jobs.ashbyhq.com/saronic | 2 |
| Shield AI | ashby | https://jobs.ashbyhq.com/shield-ai | 2 |
| Stripe | greenhouse | https://boards.greenhouse.io/stripe | 2 |
| Supabase | ashby | https://jobs.ashbyhq.com/supabase | 2 |
| Tavily | greenhouse | https://boards.greenhouse.io/tavily | 2 |
| Vannevar Labs | greenhouse | https://boards.greenhouse.io/vannevarlabs | 2 |
| Alloy | greenhouse | https://boards.greenhouse.io/alloy | 1 |
| Arize AI | greenhouse | https://boards.greenhouse.io/arizeai | 1 |
| Asana | greenhouse | https://boards.greenhouse.io/asana | 1 |
| Assort Health | ashby | https://jobs.ashbyhq.com/assorthealth | 1 |
| Baseten | ashby | https://jobs.ashbyhq.com/baseten | 1 |
| Black Forest Labs | ashby | https://jobs.ashbyhq.com/black-forest-labs | 1 |
| Brex | greenhouse | https://boards.greenhouse.io/brex | 1 |
| Cartesia | ashby | https://jobs.ashbyhq.com/cartesia | 1 |
| Cognition | ashby | https://jobs.ashbyhq.com/cognition | 1 |
| Cresta | greenhouse | https://boards.greenhouse.io/cresta | 1 |
| Ema | ashby | https://jobs.ashbyhq.com/ema | 1 |
| Exa | ashby | https://jobs.ashbyhq.com/exa | 1 |
| Fiddler AI | ashby | https://jobs.ashbyhq.com/fiddler-ai | 1 |
| Figma | greenhouse | https://boards.greenhouse.io/figma | 1 |
| Firecrawl | ashby | https://jobs.ashbyhq.com/firecrawl | 1 |
| Hightouch | greenhouse | https://boards.greenhouse.io/hightouch | 1 |
| Honeycomb | greenhouse | https://boards.greenhouse.io/honeycomb | 1 |
| LangChain | ashby | https://jobs.ashbyhq.com/langchain | 1 |
| Level AI | lever | https://jobs.lever.co/levelai | 1 |
| Luma AI | ashby | https://jobs.ashbyhq.com/lumaai | 1 |
| Middesk | ashby | https://jobs.ashbyhq.com/middesk | 1 |
| Monte Carlo | ashby | https://jobs.ashbyhq.com/montecarlodata | 1 |
| n8n | ashby | https://jobs.ashbyhq.com/n8n | 1 |
| Neon | ashby | https://jobs.ashbyhq.com/neon | 1 |
| Perplexity | ashby | https://jobs.ashbyhq.com/perplexity | 1 |
| Physical Intelligence | ashby | https://jobs.ashbyhq.com/physicalintelligence | 1 |
| Pinecone | ashby | https://jobs.ashbyhq.com/pinecone | 1 |
| Pure Storage | greenhouse | https://boards.greenhouse.io/purestorage | 1 |
| Replit | ashby | https://jobs.ashbyhq.com/replit | 1 |
| RunPod | ashby | https://jobs.ashbyhq.com/runpod | 1 |
| Stability AI | greenhouse | https://boards.greenhouse.io/stabilityai | 1 |
| StackBlitz | greenhouse | https://boards.greenhouse.io/stackblitz | 1 |
| Suki | greenhouse | https://boards.greenhouse.io/suki | 1 |
| Surge AI | ashby | https://jobs.ashbyhq.com/surge-ai | 1 |
| Tavily | ashby | https://jobs.ashbyhq.com/tavily | 1 |
| Tennr | ashby | https://jobs.ashbyhq.com/tennr | 1 |
| Thoughtworks | greenhouse | https://boards.greenhouse.io/thoughtworks | 1 |
| Tines | greenhouse | https://boards.greenhouse.io/tines | 1 |
| Together AI | greenhouse | https://boards.greenhouse.io/togetherai | 1 |
| Vapi | ashby | https://jobs.ashbyhq.com/vapi | 1 |
| Vercel | greenhouse | https://boards.greenhouse.io/vercel | 1 |
| Warp | greenhouse | https://boards.greenhouse.io/warp | 1 |
| WorkOS | ashby | https://jobs.ashbyhq.com/workos | 1 |
| Writer | ashby | https://jobs.ashbyhq.com/writer | 1 |

### Resolved boards with no FDE posting at collection time

[Abnormal Security](https://boards.greenhouse.io/abnormalsecurity), [Abridge](https://jobs.ashbyhq.com/abridge), [Airbyte](https://jobs.ashbyhq.com/airbyte), [Airtable](https://boards.greenhouse.io/airtable), [Airtable](https://jobs.ashbyhq.com/airtable), [Aleph Alpha](https://jobs.ashbyhq.com/alephalpha), [Algolia](https://boards.greenhouse.io/algolia), [Alloy](https://jobs.lever.co/alloy), [Ambience Healthcare](https://jobs.ashbyhq.com/ambiencehealthcare), [Andela](https://jobs.ashbyhq.com/andela), [Anomalo](https://jobs.ashbyhq.com/anomalo), [Anyscale](https://jobs.lever.co/anyscale), [Anyscale](https://jobs.ashbyhq.com/anyscale), [Arthur](https://jobs.ashbyhq.com/arthur), [Artisan](https://jobs.ashbyhq.com/artisan), [AssemblyAI](https://boards.greenhouse.io/assemblyai), [Astronomer](https://jobs.ashbyhq.com/astronomer), [Bland AI](https://jobs.ashbyhq.com/bland), [Braintrust](https://jobs.ashbyhq.com/braintrust), [Browserbase](https://jobs.ashbyhq.com/browserbase), [Cerebras](https://jobs.ashbyhq.com/cerebras), [Character.AI](https://jobs.ashbyhq.com/character), [Chroma](https://jobs.ashbyhq.com/trychroma), [Clari](https://jobs.lever.co/clari), [Clerk](https://jobs.ashbyhq.com/clerk), [Comet](https://boards.greenhouse.io/comet), [Comet](https://jobs.ashbyhq.com/comet), [Confluent](https://jobs.ashbyhq.com/confluent), [Cortex](https://boards.greenhouse.io/cortex), [Crusoe](https://jobs.ashbyhq.com/crusoe), [Dagster Labs](https://boards.greenhouse.io/dagsterlabs), [Dataiku](https://boards.greenhouse.io/dataiku), [Deepnote](https://jobs.ashbyhq.com/deepnote), [Descript](https://boards.greenhouse.io/descript), [Distyl AI](https://jobs.ashbyhq.com/distyl), [Drata](https://jobs.ashbyhq.com/drata), [Dropbox](https://boards.greenhouse.io/dropbox), [Dust](https://jobs.ashbyhq.com/dust), [E2B](https://jobs.ashbyhq.com/e2b), [Elastic](https://boards.greenhouse.io/elastic), [Eleos Health](https://boards.greenhouse.io/eleoshealth), [Eleos Health](https://jobs.ashbyhq.com/eleos), [Elicit](https://jobs.ashbyhq.com/elicit), [Epirus](https://boards.greenhouse.io/epirus), [Eve](https://boards.greenhouse.io/eve), [Extend](https://boards.greenhouse.io/extend), [Extend](https://jobs.ashbyhq.com/extend), [Factory](https://jobs.ashbyhq.com/factory), [Figure](https://boards.greenhouse.io/figure), [Figure](https://jobs.ashbyhq.com/figure), [Fivetran](https://boards.greenhouse.io/fivetran), [Galileo](https://boards.greenhouse.io/galileo), [Glean](https://boards.greenhouse.io/gleanwork), [Gong](https://boards.greenhouse.io/gongio), [Gumloop](https://jobs.ashbyhq.com/gumloop), [Handshake AI](https://boards.greenhouse.io/handshake), [Harvey](https://jobs.ashbyhq.com/harvey), [Hex](https://boards.greenhouse.io/hextechnologies), [Hex](https://jobs.ashbyhq.com/hex), [Hightouch](https://jobs.ashbyhq.com/hightouch), [Ideogram](https://jobs.ashbyhq.com/ideogram), [Imbue](https://boards.greenhouse.io/imbue), [Imbue](https://jobs.lever.co/imbue), [Inflection AI](https://boards.greenhouse.io/inflectionai), [Invisible Technologies](https://boards.greenhouse.io/invisible), [Krea](https://jobs.ashbyhq.com/krea), [Labelbox](https://jobs.lever.co/labelbox), [Lambda](https://jobs.ashbyhq.com/lambda), [Langfuse](https://jobs.ashbyhq.com/langfuse), [Level AI](https://jobs.ashbyhq.com/level-ai), [Liquid AI](https://jobs.ashbyhq.com/liquid-ai), [LivePerson](https://boards.greenhouse.io/liveperson), [LlamaIndex](https://jobs.ashbyhq.com/llamaindex), [Magic](https://boards.greenhouse.io/magic), [Mercor](https://jobs.ashbyhq.com/mercor), [Merge](https://boards.greenhouse.io/merge), [Merge](https://jobs.ashbyhq.com/merge), [Mistral AI](https://jobs.lever.co/mistral), [Nabla](https://jobs.ashbyhq.com/nabla), [Neon](https://jobs.lever.co/neon), [Nightfall AI](https://jobs.ashbyhq.com/nightfall-ai), [Norm AI](https://jobs.ashbyhq.com/norm-ai), [Observe.AI](https://boards.greenhouse.io/observeai), [Omni](https://jobs.ashbyhq.com/omni), [Otter.ai](https://boards.greenhouse.io/otterai), [Patronus AI](https://jobs.ashbyhq.com/patronus), [Persona](https://jobs.lever.co/withpersona), [Persona](https://jobs.ashbyhq.com/persona), [Pika](https://jobs.ashbyhq.com/pika), [PlanetScale](https://boards.greenhouse.io/planetscale), [PolyAI](https://boards.greenhouse.io/polyai), [Poolside](https://jobs.ashbyhq.com/poolside), [Prefect](https://jobs.ashbyhq.com/prefect), [Pure Storage](https://jobs.ashbyhq.com/purestorage), [Rad AI](https://jobs.ashbyhq.com/radai), [Rasa](https://jobs.ashbyhq.com/rasa), [Read AI](https://jobs.ashbyhq.com/read-ai), [Rebellion Defense](https://boards.greenhouse.io/rebelliondefense), [Reka](https://jobs.ashbyhq.com/reka), [Relevance AI](https://jobs.ashbyhq.com/relevanceai), [Rilla](https://jobs.ashbyhq.com/rilla), [Rogo](https://jobs.ashbyhq.com/rogo), [Rubrik](https://boards.greenhouse.io/rubrik), [Runway](https://jobs.ashbyhq.com/runway), [Safe Superintelligence](https://jobs.ashbyhq.com/ssi), [Samsara](https://boards.greenhouse.io/samsara), [Saronic](https://jobs.lever.co/saronic), [Sendbird](https://boards.greenhouse.io/sendbird), [Sesame](https://jobs.lever.co/sesame), [Sesame](https://jobs.ashbyhq.com/sesame), [Shield AI](https://jobs.lever.co/shieldai), [Sierra](https://jobs.ashbyhq.com/sierra), [Sigma Computing](https://boards.greenhouse.io/sigmacomputing), [Snyk](https://jobs.ashbyhq.com/snyk), [Speechmatics](https://boards.greenhouse.io/speechmatics), [Stytch](https://jobs.ashbyhq.com/stytch), [Suno](https://jobs.ashbyhq.com/suno), [Synthesia](https://jobs.ashbyhq.com/synthesia), [Tecton](https://jobs.lever.co/tecton), [Temporal](https://jobs.ashbyhq.com/temporal), [Thinking Machines](https://jobs.ashbyhq.com/thinkingmachines), [Thoughtworks](https://jobs.ashbyhq.com/thoughtworks), [Toptal](https://jobs.lever.co/toptal), [Torq](https://boards.greenhouse.io/torq), [Turing](https://boards.greenhouse.io/turing), [Turing](https://jobs.ashbyhq.com/turing), [Twilio](https://boards.greenhouse.io/twilio), [Typeface](https://boards.greenhouse.io/typeface), [Udio](https://boards.greenhouse.io/udio), [Unstructured](https://jobs.ashbyhq.com/unstructured), [Vanta](https://jobs.ashbyhq.com/vanta), [Vectara](https://boards.greenhouse.io/vectara), [Vercel](https://jobs.ashbyhq.com/vercel), [Verkada](https://boards.greenhouse.io/verkada), [Verkada](https://jobs.ashbyhq.com/verkada), [Warp](https://jobs.ashbyhq.com/warp), [Weaviate](https://jobs.ashbyhq.com/weaviate), [Wiz](https://boards.greenhouse.io/wizinc), [Wiz](https://jobs.ashbyhq.com/wiz), [World Labs](https://jobs.ashbyhq.com/worldlabs), [xAI](https://boards.greenhouse.io/xai), [You.com](https://boards.greenhouse.io/youcom), [Zapier](https://jobs.ashbyhq.com/zapier), [Zilliz](https://jobs.lever.co/zilliz)

## Hacker News threads

- [Ask HN: Who is hiring? (September 2026)](https://news.ycombinator.com/item?id=49522897)
- [Ask HN: Who is hiring? (August 2026)](https://news.ycombinator.com/item?id=49156683)
- [Ask HN: Who is hiring? (July 2026)](https://news.ycombinator.com/item?id=48747976)
- [Ask HN: Who is hiring? (June 2026)](https://news.ycombinator.com/item?id=48357725)
- [Ask HN: Who is hiring? (May 2026)](https://news.ycombinator.com/item?id=47975571)
- [Ask HN: Who is hiring? (April 2026)](https://news.ycombinator.com/item?id=47601859)
- [Ask HN: Who is hiring? (March 2026)](https://news.ycombinator.com/item?id=47219668)
- [Ask HN: Who is hiring? (February 2026)](https://news.ycombinator.com/item?id=46857488)
- [Ask HN: Who is hiring? (January 2026)](https://news.ycombinator.com/item?id=46466074)
- [Ask HN: Who is hiring? (December 2025)](https://news.ycombinator.com/item?id=46108941)
