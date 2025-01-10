# visualization.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps

"""
This file contains the API endpoints for visualizing the user's vocabulary graph.
It should show a graph representation basing on Graph, GraphNode, and GraphEdge models.
According to different mastery scores of the nodes, the nodes on the graph should be colored differently.
The higher the mastery score, the greener the color, otherwise, the redder the color.
Default color is grey when mastery score is 0.5. But if it ever comes back to 0.5, it should be colored as yellow.

User could click on any node, a video window should pop up and show the lines that contain the word in the node.
If the user clicks on the video, the video should start playing from the start of the line, and stop at the end of
the line automatically.

"""

router = APIRouter()


@router.get("/{user_id}")
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
