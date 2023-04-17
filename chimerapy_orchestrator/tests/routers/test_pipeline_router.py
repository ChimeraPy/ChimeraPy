import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chimerapy_orchestrator.pipeline_service.pipelines import Pipelines
from chimerapy_orchestrator.registry import nodes_registry
from chimerapy_orchestrator.routers.pipeline_router import PipelineRouter
from chimerapy_orchestrator.tests.base_test import BaseTest
from chimerapy_orchestrator.utils import uuid


class TestPipelineRouter(BaseTest):
    @pytest.fixture(scope="class")
    def pipeline_client(self):
        app = FastAPI()
        app.include_router(PipelineRouter(Pipelines()))
        yield TestClient(app)

    def test_get_pipelines(self, pipeline_client):
        response = pipeline_client.get("/pipeline/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_nodes(self, pipeline_client):
        response = pipeline_client.get("/pipeline/list-nodes")
        assert response.status_code == 200
        assert len(response.json()) == len(nodes_registry)

    def test_create_pipeline(self, pipeline_client):
        pipeline = pipeline_client.put(
            "/pipeline/create",
            json={"name": "test_pipeline", "description": "test_description"},
        )
        assert pipeline.status_code == 200
        json_response = pipeline.json()
        assert json_response["name"] == "test_pipeline"
        assert json_response["description"] == "test_description"
        assert json_response["id"] is not None
        assert json_response["nodes"] == []
        assert json_response["edges"] == []

    def test_list_pipelines(self, pipeline_client):
        pipelines = pipeline_client.get("/pipeline/list")
        assert pipelines.status_code == 200
        assert len(pipelines.json()) == 1

    def test_node_edge_operations(self, pipeline_client):
        pipeline = pipeline_client.get("/pipeline/list").json()[0]
        pipeline_id = pipeline["id"]

        # Add nodes
        webcam_node = pipeline_client.post(
            f"/pipeline/add-node/{pipeline_id}",
            json={"name": "WebcamNode", "registry_name": "WebcamNode"},
        )

        assert webcam_node.status_code == 200
        webcam_node_json = webcam_node.json()
        assert webcam_node_json["name"] == "WebcamNode"
        assert webcam_node_json["registry_name"] == "WebcamNode"
        assert webcam_node_json["id"] is not None
        assert webcam_node_json["type"] == "SOURCE"

        show_window_node = pipeline_client.post(
            f"/pipeline/add-node/{pipeline_id}",
            json={"name": "ShowWindow", "registry_name": "ShowWindow"},
        )

        assert show_window_node.status_code == 200
        show_window_node_json = show_window_node.json()
        assert show_window_node_json["name"] == "ShowWindow"
        assert show_window_node_json["registry_name"] == "ShowWindow"
        assert show_window_node_json["id"] is not None
        assert show_window_node_json["type"] == "SINK"

        # Add edges
        edge_id = uuid()
        edge = pipeline_client.post(
            f"/pipeline/add-edge/{pipeline_id}",
            json={
                "source": webcam_node_json,
                "sink": show_window_node_json,
                "id": edge_id,
            },
        )

        assert edge.status_code == 200
        edge_json = edge.json()
        assert edge_json["source"]["id"] == webcam_node_json["id"]
        assert edge_json["sink"]["id"] == show_window_node_json["id"]
        assert edge_json["id"] == edge_id

        # Remove edge
        edge = pipeline_client.post(
            f"/pipeline/remove-edge/{pipeline_id}",
            json={
                "source": webcam_node_json,
                "sink": show_window_node_json,
                "id": edge_id,
            },
        )

        assert edge.status_code == 200
        edge_json = edge.json()
        assert edge_json["source"]["id"] == webcam_node_json["id"]
        assert edge_json["sink"]["id"] == show_window_node_json["id"]
        assert edge_json["id"] == edge_id

        # Remove node
        node = pipeline_client.post(
            f"/pipeline/remove-node/{pipeline_id}", json=webcam_node_json
        )

        assert node.status_code == 200
        node_json = node.json()
        assert node_json["id"] == webcam_node_json["id"]
        assert node_json["name"] == webcam_node_json["name"]
        assert node_json["registry_name"] == webcam_node_json["registry_name"]
        assert node_json["type"] == webcam_node_json["type"]

        # Remove pipeline
        pipeline = pipeline_client.delete(f"/pipeline/remove/{pipeline_id}")

        assert pipeline.status_code == 200
        pipeline_json = pipeline.json()
        assert pipeline_json["id"] == pipeline_id
        assert pipeline_json["name"] == "test_pipeline"
        assert pipeline_json["description"] == "test_description"
        assert pipeline_json["nodes"] == [show_window_node_json]