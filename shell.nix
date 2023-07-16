let
  pkgs = import <nixpkgs> { };
  pname = "slack-python-logging";
  vsextensions = (with pkgs.vscode-extensions; [
    ms-azuretools.vscode-docker
    ms-python.python
    ms-vsliveshare.vsliveshare
    redhat.vscode-yaml
    streetsidesoftware.code-spell-checker
    vscodevim.vim
    matangover.mypy
    charliermarsh.ruff
  ]) ++ pkgs.vscode-utils.extensionsFromVscodeMarketplace [
    {
      publisher = "42Crunch";
      name = "vscode-openapi";
      version = "4.18.4";
      sha256 = "sha256-lv4dUJDOFPemvS8YTD12/PjeTevWhR76Ex8qHjQH3vY=";
    }
    {
          publisher = "ms-python";
          name = "black-formatter";
          version = "2023.5.11841009";
          sha256 = "sha256-zmEDAdj/7ZyzXzh+iPes6LMIA7+63wZZB2ZD65kKp8I=";
    }
    {
          publisher = "ms-python";
          name = "isort";
          version = "2023.9.11781018";
          sha256 = "sha256-ev+gSQP+Q1AEw+r1Uahi1TI+docalcC1iWO29N1L5VE=";
    }
  ]; 
  vscode-nocode-plugins-ape = pkgs.vscode-with-extensions.override {
    vscodeExtensions = vsextensions;
  };
in
pkgs.mkShell rec {
  buildInputs = with pkgs; [
    git
    awscli2
    aws-vault

    ruff
    mypy
    black

    pgcli postgresql

    python310
    python310Packages.pip
    python310Packages.virtualenv
    python310Packages.numpy
    python310Packages.pandas

    vscode-nocode-plugins-ape

  ];

}
