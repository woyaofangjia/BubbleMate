from backend.storage.database import save_knowledge, get_knowledge_graph

save_knowledge('口味', '非常抱歉您对口味不满意，我们会尽快为您处理。', '免费重做或退款')
save_knowledge('服务', '非常抱歉给您带来不好的服务体验。', '赠送5元优惠券')
save_knowledge('配送', '非常抱歉配送超时，我们会加快处理。', '下次免配送费')

graph = get_knowledge_graph()
print('知识图谱结构:')
for node in graph:
    print(f"  {node['content']} (id={node['id']}, reviewed={node['reviewed']})")
    for child in node['children']:
        print(f"    └─ {child['node_type']}: {child['content']}")