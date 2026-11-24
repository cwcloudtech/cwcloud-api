import os
import yaml
import shutil
import gitlab

from git import Repo
from pathlib import Path
from typing import Optional
from fastapi.responses import JSONResponse
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from schemas.Kubernetes import ExternalChart

from utils.file import read_file_content
from utils.gitlab import GIT_HELMCHARTS_REPO_URL, push_files_to_repository, GIT_DEFAULT_TOKEN, GIT_USERNAME
from utils.observability.cid import get_current_cid
from utils.common import AUTOESCAPE_EXTENSIONS

CHARTS_REPO_PATH = os.getenv('LOCAL_CLONE_CHARTS_PATH', '/cloned_charts')

git_url = f'https://{GIT_USERNAME}:{GIT_DEFAULT_TOKEN}@{GIT_HELMCHARTS_REPO_URL.replace("https://", "")}'

def push_charts(
    project_id,
    gitlab_host,
    deployment_name: str,
    namespace: str,
    environment_name: str,
    values: str,
    readme: str,
    token: str,
    charts: list[str],
    external_charts: Optional[list[ExternalChart]],
    args: Optional[dict[str, any]],
):
    if None in (GIT_DEFAULT_TOKEN, GIT_USERNAME, CHARTS_REPO_PATH, GIT_HELMCHARTS_REPO_URL):
        raise ValueError(
            "One or more required environment variables are missing.")

    file_loader = FileSystemLoader(
        str(Path(__file__).resolve().parents[2]) + "/templates/kubernetes/app"
    )
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template("Chart.yaml.j2")
    doc_template = Template(readme)
    value_template = Template(values)
    root_dir = f"{CHARTS_REPO_PATH}_{project_id}"

    try:
        charts_files = []
        gitlab_connection = gitlab.Gitlab(url=gitlab_host, private_token=token)

        path_tpl = "{}/{}"
        root_dir = f"{CHARTS_REPO_PATH}_{project_id}"
        charts_path = "{}/charts".format(root_dir)
        clone_chart_repo(git_url, root_dir, charts_path, charts)

        for root, dirs, files in os.walk(charts_path):
            new_root = root.replace(root_dir, "")
            if "external-chart.yaml" not in files:
                for file in files:
                    root.replace(root_dir, "")
                    charts_files.append(
                        {
                            "path": path_tpl.format(new_root, file),
                            "content": read_file_content(path_tpl.format(root, file)),
                        }
                    )
            else:
                get_external_dependency_data(root, external_charts, charts)

        charts_files.extend([
            {
                "path": "/Chart.yaml",
                "content": template.render(
                    name=deployment_name,
                    dependencies=charts,
                    external_dependencies=external_charts,
                ),
            },
            {
                "path": "/values.yaml",
                "content": value_template.render(
                    env_hashed_name=namespace,
                    environment=environment_name,
                    args=args
                ),
            },
            {
                "path": "/README.md",
                "content": doc_template.render(
                    name=namespace,
                    deployment_name=deployment_name,
                    dependencies=charts,
                    external_dependencies=external_charts,
                    args=args,
                ),
            }]
        )
        push_files_to_repository(
            charts_files, gitlab_connection, project_id, "main", "Added Manifest"
        )
        shutil.rmtree(root_dir)
    except Exception as e:
        return JSONResponse(
            content={
                "status": "ko",
                "message": "error pushing charts",
                "cid": get_current_cid(),
            },
            status_code=500,
        )

    return JSONResponse(
        content={"status": "ok", "message": "charts pushed"}, status_code=200
    )



def get_external_dependency_data(root: str, external_charts: list[ExternalChart], charts: list[str]):
    with open(f"{root}/external-chart.yaml", 'r') as yaml_file:
        external_chart_file = yaml.safe_load(yaml_file)
        new_chart = ExternalChart(
            name=external_chart_file["name"],
            version=external_chart_file["version"],
            repository=external_chart_file["repository"]
        )
        external_charts.append(new_chart)
        dependency = root.split("/")[-1]
        if dependency in charts:
            charts.remove(dependency)
        
def clone_chart_repo(git_url, root_dir, charts_path,charts):
    if os.path.exists(root_dir):
        shutil.rmtree(root_dir)
        
    Repo.clone_from(git_url, root_dir, branch='main')

    path_tpl = "{}/{}"
    for dir in os.listdir(charts_path):
        if dir not in charts:
            shutil.rmtree(path_tpl.format(charts_path, dir))
