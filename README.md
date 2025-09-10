# TransLibEval: A Benchmark for Evaluating Code Translation with Third-Party Libraries

TransLibEval is the first library-centric code translation benchmark presented in the paper " TransLibEval:  A Library-Centric Benchmark for Code Translation Across Python,  Java, and C++. "  Feel free to contact us for further information or to submit new results.



## Dataset

TransLibEval, a TPL-focused, multi-PL code translation benchmark with 200 method-level tasks built from a Python calibration across 50 widely used libraries (data processing, ML, web, visualization, NLP, utilities, etc.). Each Python task defines exactly one top-level class with a single instance method that calls a third-party API; method signatures use primitive types only. For every task, we provide parallel Java and C++ counterparts plus equivalent unit tests (Python unittest, Java JUnit via Maven, C++ GoogleTest via NuGet).

Each task’s test suite contains exactly five test cases—normal input, edge input, exception handling, type validation, and resource-constraint—executed across all three languages. Code is comment-free, PEP 8 compliant, and Java/C++ follow official style and library selection rules.



## Open-Source Code

To make third-party-library–aware code translation comparable across different LLMs, this repo ships lightweight invocation scripts per provider. Each script unifies a common CLI and prompt template for translation, so results are reproducible across models.

+ **DeepSeek Invocation Script:** The `deepseek.py` file calls the DeepSeek model with a predefined prompt for code translation.
+ **Qwen Invocation Script:** The `qwen-max.py` file invokes Alibaba Cloud models (Tongyi) with the standardized prompt and CLI.
+ etc.



### Execute strategy code generation

All generation/invocation scripts live under `code/generate_strategies/<strategy_name>/` (one folder per strategy).  Concretely: 

- **Direct** / **RA(method)** — run the provider script **directly**.

  ```bash
  # <provider> ∈ {deepseek.py, qwen-max.py, ...}
  python code/generate_strategies/Direct/<provider>
  python code/generate_strategies/RA-method/<provider>
  ```

- **IR strategies (3 variants)** — run the **target-language–specific** script under that strategy.

  ```bash
  # <ir> ∈ {IR（*）, e.g., IR（CoT）, IR（pseudocode）, IR(summary)}; <target_lang> ∈ {java, cpp, python}
  python code/generate_strategies/<ir>/<target_lang>/<provider>
  ```

- **RA(name)** — first extract the function signature for the **target language**, then run the provider script.

  ```bash
  # Step 1: signature extraction
  # <source_lang> ∈ {java, cpp, python}
  python code/generate_strategies/RA-name/<target_lang>/signature.py \
    --out <source_lang>_api_results
  
  # Step 2: translation with signature
  python code/generate_strategies/RA-name/<target_lang>/<provider>
  ```

- `<provider>` examples: `deepseek.py`, `qwen-max.py`, etc.
- All scripts share a common CLI (e.g., `--temperature`, `--max_tokens`, `--retries`) for consistent comparisons.



### Test Suites

We provide language-specific automated test harnesses for Python (unittest),  Java (JUnit via Maven), and C++ (GoogleTest via CMake/CTest).  Each task includes exactly five test cases—normal input, edge input, exception handling, type validation, and resource-constraint—to enforce behavioral equivalence across languages.



**Dependencies**

Before running any tests, install the third-party libraries listed under `data/requirements/`:

```
data/dependencies/
├── requirements.txt         # Python deps
├── java_third_party.txt     # Java deps (add to your build tool)
└── cpp_third_party.txt      # C++ deps (install via pkg manager)
```

- **Python:**

  ```
  python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
  pip install -r data/requirements/requirements.txt
  ```

- **Java:** Add the artifacts from `java_third_party.txt` to your **Maven/Gradle** build (or download JARs and update your `CLASSPATH`). Ensure versions match the list.

- **C++:** Install libraries from `cpp_third_party.txt` using your platform’s package manager (e.g., `apt`, `brew`) or a C++ package manager (e.g., **vcpkg**, **Conan**). Make sure headers and link libraries are discoverable by your compiler/CMake toolchain.



**Python**

+ Place the code to be tested under `code/test_suites/python/` as a **packaged folder** named `<source_lang>_<target_lang>` (e.g., `python_java`, `python_cpp`). Then run the following in order:
  1. **Compile & build:** `run_<source_lang>.py`
  2. **Bundle passing artifacts:** `copypy_<source_lang>.py`
  3. **Execute unit tests sequentially:** `automate_test_<source_lang>.py`

**C++**

+ Place the code to be tested under `code/test_suites/cpp/FunctionBuildTest/`, packaged inside the `src/` folder. Then run:

  1. **Compile & build:**

     ```
     cd code/test_suites/cpp/FunctionBuildTest
     bash build_script.sh
     ```

  2. **Bundle passing artifacts:**

     ```
     python select_tests.py
     ```

  3. **Execute unit tests sequentially:** (from the parent folder)

     ```
     cd ..
     python automate_test.py
     ```

**Java**

+ Configure dependencies & paths. Set up required libraries (e.g., via Maven/Gradle or local jars) and update all path placeholders inside the scripts to match your workspace.
+ Run integrator in a separate project. Execute `ProjectIntegrator.java` from an unrelated/bootstrapping project to assemble dependencies and lay out the build structure.
+ Discover & test in the code project. In the project that contains your functional code and test code, run `MethodFinder.java` first, then `JSONTestRunner.java` to execute the tests based on the discovered methods.



Each run produces a **JSON report** with the test results (the script prints the exact path). If model outputs contain superficial differences (formatting, minor strings) that cause spurious mismatches, use the regex-based normalization utilities under `normalization/` to post-process and align outputs with the test cases.



## Research Questions (RQs)

### RQ1 (Overall Correctness)

How do recent LLMs perform on library-centric code translation? Compared with general code translation, library-centric translation introduces additional challenges due to the need for correct recognition, import, and use of third-party libraries. Given the increasing prevalence of external library APIs in modern software development, it becomes critical to understand how well LLMs can handle such dependencies across languages.

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/20250910114103143.png)



### RQ2 (Translation Strategies)

How do different translation strategies affect the performance of recent LLMs on library-centric code translation? Developers may adopt different prompting strategies like direct translation, Intermediate Representation (IR)-guided translation, or retrieval-augmented translation. Evaluating how these strategies impact the handling of library dependencies can offer practical guidance for prompt engineering and model deployment.

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/rq2.png)



### RQ3 (Library Dependency Awareness)

How do the LLMs perform in identifying necessary and available libraries? Library-centric code translation often requires not just syntax conversion but also awareness of the necessary libraries for implementing equivalent functionalities. Considering that the library mappings between different PLs are not always one-to-one, LLMs have to infer a limited library set to accomplish the translation task in this work. Nonetheless, LLMs’ above-mentioned ability is still unknown, and the corresponding investigation has not been extensively conducted before, thus motivating us to delve into this RQ.

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/20250910114256860.png)

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/20250910114318937.png)



### RQ4 (Failed Cases Analysis)

What kind of errors do LLMs make in library-centric translation, and how frequent are they? While prior work has examined LLM failures in method-, class- or even repo-level translation, their included libraries, even in repo-level, are limited as shown in Section 2. Thus, a large-scale fine-grained analysis of libraryrelated errors is still lacking, and identifying these failure modes can help the community develop more targeted improvements for LLM-based code translation systems.

For the precise taxonomy and operational definitions of error types, see **`failed_cases_report.pdf`**.

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/20250910114335463.png)

![](https://blogxiaozheng.oss-cn-beijing.aliyuncs.com/images/20250910114353580.png)



## Getting Started

1. **Clone the repository** and set up the environment.
2. **Data Preparation**: Ensure the TransLibEval dataset is available and ready for LLM invocation.
3. **Running Experiments**: Use the **Execute strategy code generation** flow described in **Open-Source Code** (Direct, RA(method), IR variants, RA(name)), then run the **automated test suites** as outlined in **Test Suites** (Python/Java/C++).



## Requirements

+ **Python** 3.9 +
+ **C++** CMake ≥ 3.15, a C++20 compiler, and the following deps (recommended via **vcpkg**)
+ **Java** JDK 23
