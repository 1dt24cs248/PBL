"""Add synthetic room geometry and indoor navigation graph."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "0004_floorplan_navigation"
down_revision = "0003_timetable_foundation"
branch_labels = None
depends_on = None


def _artifact() -> dict:
    path = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "floorplan.json"
    return json.loads(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    with op.batch_alter_table("rooms") as batch:
        for column in ("x", "y", "w", "h"):
            batch.add_column(sa.Column(column, sa.Float(), nullable=False, server_default="0"))

    op.create_table(
        "nav_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("node_key", sa.String(100), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("room_id", sa.String(20), nullable=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"),
    )
    op.create_index("ix_nav_nodes_node_key", "nav_nodes", ["node_key"], unique=True)
    op.create_index("ix_nav_nodes_floor", "nav_nodes", ["floor"])
    op.create_index("ix_nav_nodes_room_id", "nav_nodes", ["room_id"])

    op.create_table(
        "nav_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_node_id", sa.Integer(), sa.ForeignKey("nav_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_node_id", sa.Integer(), sa.ForeignKey("nav_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("floor_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wait_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bidirectional", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"),
        sa.UniqueConstraint("from_node_id", "to_node_id", "mode", name="uq_nav_edges_direction_mode"),
    )
    op.create_index("ix_nav_edges_from_node_id", "nav_edges", ["from_node_id"])
    op.create_index("ix_nav_edges_to_node_id", "nav_edges", ["to_node_id"])

    bind = op.get_bind()
    artifact = _artifact()
    nodes = [node for floor in artifact["floors"] for node in floor["nodes"]]
    for node in nodes:
        bind.execute(sa.text("""
            INSERT INTO nav_nodes (node_key, floor, node_type, x, y, room_id, provenance)
            VALUES (:node_key, :floor, :node_type, :x, :y, :room_id, :provenance)
        """), node)
    node_ids = {
        key: identifier for identifier, key in bind.execute(
            sa.text("SELECT id, node_key FROM nav_nodes")
        ).all()
    }
    for edge in artifact["edges"]:
        bind.execute(sa.text("""
            INSERT INTO nav_edges (from_node_id, to_node_id, mode, distance_m, floor_delta,
                                   wait_seconds, bidirectional, provenance)
            VALUES (:from_node_id, :to_node_id, :mode, :distance_m, :floor_delta,
                    :wait_seconds, :bidirectional, :provenance)
        """), {
            "from_node_id": node_ids[edge["from"]], "to_node_id": node_ids[edge["to"]],
            "mode": edge["mode"], "distance_m": edge["distance_m"],
            "floor_delta": edge["floor_delta"], "wait_seconds": edge["wait_seconds"],
            "bidirectional": edge["bidirectional"], "provenance": edge["provenance"],
        })

    rooms = {row["room_id"]: row["geometry"] for floor in artifact["floors"] for row in floor["rooms"]}
    for room_id, geometry in rooms.items():
        bind.execute(sa.text("""
            UPDATE rooms SET x=:x, y=:y, w=:w, h=:h
            WHERE number=:room_id AND building_id=(SELECT id FROM buildings WHERE code='A')
        """), {"room_id": room_id, **geometry})


def downgrade() -> None:
    op.drop_index("ix_nav_edges_to_node_id", table_name="nav_edges")
    op.drop_index("ix_nav_edges_from_node_id", table_name="nav_edges")
    op.drop_table("nav_edges")
    op.drop_index("ix_nav_nodes_room_id", table_name="nav_nodes")
    op.drop_index("ix_nav_nodes_floor", table_name="nav_nodes")
    op.drop_index("ix_nav_nodes_node_key", table_name="nav_nodes")
    op.drop_table("nav_nodes")
    with op.batch_alter_table("rooms") as batch:
        for column in ("h", "w", "y", "x"):
            batch.drop_column(column)
