from string import Template

document_template = Template('<document index="$doc_num">\n$chunk_text\n</document>')

header_template = Template(
    "\n".join(
        ["Based ONLY on the <context> documents provided below, answer the user's question.", "Question: $query"]
    )
)
