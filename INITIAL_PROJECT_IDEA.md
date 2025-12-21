How to accelerate learning / absorption of knowledge?

Raw input data:
- personal
  - papers (with highlights and annotations, via the MacOS Books app)
  - blog posts, websites, articles (with highlights, via Raindrop)
  - books (mostly physical books with highlights and annotations)
  - code, repositories (my own as well as starred other repos)
  - idea collections
- work
  - code (work repositories)
  - meeting notes
  - design proposals
  - Slack conversations
  - notes

1. How to extract and summarize the most salient data from all those sources? (mostly a requirement on LLMs)
2. How to improve learning & solidify knowledge? (a requirement on human reader / learner)

These two questions have different requirements and can be solved independently. However, we can solve 1 in a way that optimizes value for 2.

Open questions:
- What does research have to say about maximizing learning?
- Passive vs active learning, i.e. do vs read/consume?
- Deliberate practice?

Goal:
- Build a queryable knowledge base and knowledge graph - similar to what the note taking app Obsidian provides. An Obsidian plugin [Neo4J Graph View](https://www.obsidianstats.com/plugins/neo4j-graph-view) provides a conversion tool from Obsidian notes to a true graph DB.

Learning is about establishing connections between diverse and disconnected topics and fields. To what extent do we want to outsource establishing these connections to automated note taking and LLM summarization vs. keeping it in "human memory"?

Can we connect [Raindrop](https://raindrop.io/) (via API) to Obsidian to extract bookmarked pages + highlights (i.e. the portions I personally find important)?

Summarization + highlights + follow-up tasks + auto-generated exercises to solidify knowledge

Use Obsidian + .md files as the knowledge hub or rather the raw encoded knowledge from which one can derive various downstream knowledge, tasks, connections, exercises, quizzes, etc.

Once data is ingested into the knowledge hub we can use an LLM / learning assistant to provide curated exercises.

Questions:
- How should this knowledge base be organized into an LLM-amenable hierarchy?
- Organize the content by topic or by content type (e.g. papers vs. websites vs. blog posts)? Organize the actual data storage by content type as a primary hierarchy and use tags to establish a topic-based categorization on top of the raw data.
  - Heavily rely on tags and inter-note links to establish semantic connections between pieces of raw data
- Can the knowledge graph be extracted from Obsidian?

Need to set up ingestion workflows for different data sources.

- papers (with highlights and annotations, via the MacOS Books app) --> pdf extraction/parsing + summarization via LLM
- blog posts, websites, articles (with highlights, via Raindrop) --> Raindrop API + summarization via LLM
- books (mostly physical books with highlights and annotations) --> photos + OCR + highlights parsing (e.g. via Mistral's OCR API, need to store the raw images as well but in a separate data store) + summarization via LLM
- code, repositories (my own as well as starred other repos) --> Git API (possibly [Google's Code Wiki](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/))
- idea collections

Building a knowledge base and graph is only the first step. I want to feed all of this raw and processed data into an LLM-based system to establish a deliberate practice / guided learning system that will supercharge my knowledge acquisition and learning.

Quizzes are not enough. This system should generate exercises that I need to implement or work through. Can GPT or Gemini create useful exercises? [ChatGPT Study Mode](https://openai.com/index/chatgpt-study-mode/) or [Guided Learning by Gemini](https://blog.google/outreach-initiatives/education/guided-learning/)

Make heavier use of Plugins for Obsidian
- tag wrangler
- smart connections (AI agent on top of notes)
- linter
- dataview
- waypoint, foldernote