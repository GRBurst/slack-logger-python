let
  pkgs = import <nixpkgs> { };
  pname = "slack-logger-python";
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
  vscode-slack-logger = pkgs.vscode-with-extensions.override {
    vscodeExtensions = vsextensions;
  };
  python-pkgs = ps: with ps; [
    pip
    virtualenv
  ];
  plugin-python = pkgs.python310.withPackages python-pkgs;

in

pkgs.mkShell {
  packages = [ plugin-python ];
  buildInputs = with pkgs; [
    git

    black
    isort
    ruff
    mypy

    vscode-slack-logger
  ];
}
