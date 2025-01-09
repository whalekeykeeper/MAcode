@router.get("/graph/{user_id}")
async def get_graph_data(user_id: int, session: AsyncSession = Depends(deps.get_session)):
    graph = (await session.execute(select(Graph).where(Graph.user_id == user_id))).scalar_one_or_none()
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    nodes = await session.execute(select(GraphNode).where(GraphNode.graph_id == graph.id))
    edges = await session.execute(select(GraphEdge).where(GraphEdge.graph_id == graph.id))

    return {
        "nodes": [{"id": node.id, "lemma": node.lemma, "mastery": node.mastery} for node in nodes],
        "edges": [{"source": edge.node1_id, "target": edge.node2_id, "weight": edge.weight} for edge in edges],
    }


@router.get("/node/{node_id}/lines")
async def get_lines_for_node(node_id: int, session: AsyncSession = Depends(deps.get_session)):
    node = (await session.execute(select(GraphNode).where(GraphNode.id == node_id))).scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    lines = (await session.execute(select(Line).where(Line.id.in_(node.word_ids)))).scalars().all()
    return [{"start": line.start_timestamp, "end": line.end_timestamp, "text": line.line_text} for line in lines]
