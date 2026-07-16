#!/usr/bin/env bash

playbookYaml="
- hosts: localhost
  roles:
"

generate_ansible_envs() {
    args_values_file="env/args_values_${env_name}.json"

    if [[ -f $args_values_file ]]; then
        jinjanate env/${env_name}.yml.j2 "${args_values_file}" > env/${env_name}.yml
        jinjanate env/${env_name}.md.j2 "${args_values_file}" > env/${env_name}.md
    else
        jinjanate env/${env_name}.yml.j2 > env/${env_name}.yml
        jinjanate env/${env_name}.md.j2 > env/${env_name}.md
    fi

    jinjanate .gitlab-ci.yml.j2 > "${env_name}-ci.yml"
    rm -rf ".gitlab-ci.yml.j2" "env/${env_name}.yml.j2" "env/${env_name}.md.j2" "env/args_values_${env_name}.json"
}

generate_ansible_playbook(){
for role in "${custom_roles[@]}"; do
playbookYaml+="   - ${role}
"
done
echo "$playbookYaml" > playbook-${1}.yml
} 

clean_up_files() {
    cd roles
    for file in *; do
        foundFile=0
        for role in "${custom_roles[@]}"; do
            if [[ $file = $role ]]; then
                foundFile=1
                break 
            fi 
        done
        if [[ $foundFile -eq 0 ]]; then
            rm -rf $file
        fi
    done
    cd ../
    rm -rf env
    find . -name "playbook*" -delete
    rm .gitignore
    rm .gitlab-ci.yml
    rm install.sh
    rm README.md
    rm -rf .git
}

log_msg() {
    log_level="${1}"
    msg="${2}"
    log_msg="[ansible_script][${log_level}] ${msg}"
    echo "${log_msg}"
}

while getopts e:n:c:o:m:u:l:x:d:p:t:z:b:s:g:j:q: flag; do
    case "${flag}" in
        e) environment=${OPTARG};;
        x) env_hashed_name=${OPTARG};;
        d) root_dns_zone=${OPTARG};;
        g) gitlab_project_name=${OPTARG};;
        n) env_name=${OPTARG};;
        j) gitlab_host=${OPTARG};;
        c) clone_repo=${OPTARG};;
        q) generate_dns=${OPTARG};;
        o) out_repo=${OPTARG};;
        m) git_user_email=${OPTARG};;
        b) user_email=${OPTARG};;
        u) git_user_name=${OPTARG};;
        s) centralized=${OPTARG};;
        l) gitlab_project_remote=${OPTARG};;
        p) root_password=${OPTARG};;
        t) gitlab_runner_token=${OPTARG};;
        z) access_password=${OPTARG};;
    esac
done

custom_roles=( "${@:35}" )
printf -v joined_roles '%s;' "${custom_roles[@]}"
roles_string_array=${joined_roles: :-1}
git config --global user.name "${git_user_name}"
git config --global user.email "${git_user_email}"

log_msg "INFO" "environment=${environment}, env_name=${env_name}, centralized=${centralized}"

clone_out_repo() {
    rm -rf "${gitlab_project_name}"
    git clone "${out_repo}"
    cd "${gitlab_project_name}"
    git checkout -b main 2>/dev/null || :
    git pull --rebase origin main
}

attach_instance() {
    clone_out_repo
    sed -i "/gitlab_registration_token/c\gitlab_registration_token: ${gitlab_runner_token}" env/${env_name}.yml
    sed -i "/gitlab_runner_token/c\gitlab_runner_token: changeit" env/${env_name}.yml

    git add .
    git commit -m "Attach gitlab-runner for ${env_name}"
    git pull origin main --no-edit
    git push origin main
    cd ../
    rm -rf $gitlab_project_name
}

prepare_new_repo_from_infra_playbook() {
    git clone "${clone_repo}" "infra-playbook"
    cd infra-playbook
    git pull --rebase origin main
    clean_up_files "${environment}"
    generate_ansible_playbook "${env_name}"
    mkdir -p env

    export roles_string_array="$roles_string_array"
    export env_hashed_name="$env_hashed_name"
    export gitlab_host="$gitlab_host"

    export ip_address="$ip_address"
    export out_repo="$out_repo"
    export gitlab_runner_token="$gitlab_runner_token"
    export access_password="$access_password"
    export root_password="$root_password"
    export user_email="$user_email"
    export environment="$environment"
    export env_name="$env_name"
    export gitlab_project_remote="$gitlab_project_remote"
    export centralized="$centralized"
    export generate_dns="$generate_dns"
    export root_dns_zone="$root_dns_zone"

    mkdir env
    cp ../ansible/instance_name.yml.j2 env/${env_name}.yml.j2
    cp ../ansible/instance_name.md.j2 env/${env_name}.md.j2
    cp ../ansible/args_values.json env/args_values_${env_name}.json
    cp ../ansible/.gitlab-ci.yml.j2 .
    cp ../ansible/install.sh .
    cp ../ansible/README.md .
    cp ../ansible/.gitignore .
    generate_ansible_envs
}

create_instance_and_merge_repo() {
    prepare_new_repo_from_infra_playbook
    cd ..
    clone_out_repo
    mkdir -p roles
    mkdir -p env

    for r in ../infra-playbook/roles/*; do
        role_name=$(basename $r)
        if [[ ! -d "roles/${role_name}" ]]; then
            log_msg "DEBUG" "Missing role ${role_name}, adding..."
            cp -R "${r}" "roles/"
        fi
    done

    for e in ../infra-playbook/env/*; do
        envname=$(basename $e)
        if [[ ! -f "env/${role_name}" ]]; then
            log_msg "DEBUG" "Missing env ${envname}, adding..."
            cp "${e}" "env/"
        fi
    done

    for p in ../infra-playbook/playbook*; do
        playbook_name=$(basename $p)
        if [[ ! -f "${playbook_name}" ]]; then
            log_msg "DEBUG" "Missing playbook ${playbook_name}, adding..."
            cp "${p}" "./"
        fi
    done

    ci_files=(
        "../infra-playbook/${env_name}-ci.yml"
        "../infra-playbook/.gitlab-ci.yml"
        "../infra-playbook/install.sh"
        "../infra-playbook/README.md"
        "../infra-playbook/.gitignore"
    )

    for f in "${ci_files[@]}"; do
        file_name=$(basename $f)
        if [[ -f $f ]] && [[ ! -f $file_name ]]; then
            log_msg "DEBUG" "Missing ci file ${file_name}, adding..."
            cp "${f}" "./"
        fi
    done

    git add .
    git commit -m "Setting up ansible for ${env_name}"
    git pull origin main --rebase
    git push origin main
    rm -rf ../infra-playbook
}

if [[ $centralized = "false" ]]; then
    attach_instance
else
    create_instance_and_merge_repo
fi
