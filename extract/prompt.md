# Skill extraction — posting {{ posting.id }}

You are extracting structured skill requirements from ONE job posting for a Forward Deployed Engineer-type role.
Return ONLY a JSON object matching the schema at the end. No prose, no markdown fences.

## Rules
1. Use ONLY `canonical` names from the taxonomy below. Match by meaning using the aliases and definitions. If a skill in the posting has no node, OMIT it (do not invent names).
2. Tag every skill mention with the section it appears in: `responsibility` (what you will do), `requirement` (must have), `nice_to_have` (bonus / preferred). A skill may appear in more than one section — emit one entry per section it appears in, never duplicates within a section.
3. If the posting has no explicit sections (segmentation_quality = "inferred"), decide the tag from phrasing: "you will / own / build / lead" → responsibility; "must / required / X+ years / strong" → requirement; "bonus / plus / preferred / ideally" → nice_to_have.
4. `evidence`: a quote of at most 12 words from the posting that justifies the tag.
5. `seniority`: junior | mid | senior | staff_plus | unspecified — from title and years.
6. `years_required`: the minimum years stated, else null.
7. `travel_expectation`: none | occasional (≤25% or "some") | frequent (>25%, "significant", "embedded on-site") | unspecified.
8. `customer_facing_intensity`: 1 = internal only … 5 = embedded with customers most of the time.
9. `responsibility_verbs`: exactly 5 lowercase verbs, most representative of the responsibilities section (e.g. "deploy", "scope").
10. `segmentation_quality`: copy the value given below.

## Taxonomy (closed vocabulary)
{% for ckey, skills in taxonomy.clusters.items() %}
### {{ taxonomy.cluster_labels[ckey] }} ({{ ckey }})
{% for s in skills %}- `{{ s.canonical }}` — {{ s.label }}. {{ s.definition }}.{% if s.aliases %} Aliases: {{ s.aliases|join(', ') }}{% endif %}
{% endfor %}{% endfor %}

## Posting
- title: {{ posting.title }}
- company: {{ posting.company }}
- location: {{ posting.location }}
- segmentation_quality: "{{ segments.quality }}"

## RESPONSIBILITIES
{{ segments.responsibilities or "(none found)" }}

## REQUIREMENTS
{{ segments.requirements or "(none found)" }}

## NICE_TO_HAVE
{{ segments.nice_to_have or "(none found)" }}

## OTHER (context only — extract from here ONLY if the three sections above are empty)
{{ segments.other or "(none)" }}

## Output schema
Return exactly this shape with "posting_id": "{{ posting.id }}":

Example of the exact shape (return raw JSON like this, with no code fence):
{{ schema_json }}
