    # SigmaOS-troubleshooting-tool

    System report & troubleshooting generator

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/mintreport

    ## Design principles applied
    - **Plan Before Apply**
- **Pure Rendering**
- **Determinism**
- **KISS**
- **Least Astonishment**

    ## Usage
    Verbs: `collect-plan, report, compare, export`

    ```
    $ sigma-report collect-plan --profile desktop
$ sigma-report report --facts facts.json --format text
$ sigma-report compare --before before.json --after after.json
$ sigma-report export --facts facts.json --out report.html

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
