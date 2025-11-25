# TransLibEval End-to-End Workflow Example

This section presents a single task, `function_requests_fetch_average_temperature.fetch_average_temperature`, as a representative end-to-end run of TransLibEval. The example follows the complete pipeline from source code and third-party library (TPL) usage on the Python side, through six translation strategies (Direct, three IR-based, and two retrieval-augmented), to Java target code, build and test execution, automatic metrics (CSR / PR / CA), and human evaluation of Library Dependency Awareness (LDA). Target-side implementations are referred to but not reproduced in full; the focus is on the observable artifacts in each stage.

---

## 1. Task Preparation

### 1.1 Task overview

The source program is written in Python and the target language in this run is Java. The task models a small library-like function that depends on a Python HTTP client library and is expected to be translated into an equivalent Java implementation that uses appropriate HTTP and JSON handling facilities.

The core method under evaluation is `fetch_average_temperature(city: str, days: int) -> float`. Conceptually, this method queries a weather API endpoint with a city name and a number of days, retrieves a JSON payload containing a sequence of temperature observations in Celsius, computes the arithmetic mean over all observations, rounds the result to two decimal places, and returns the rounded value as a `float`. On the Python side, HTTP and JSON are handled uniformly via the `requests` library; there is no explicit dependency on additional numeric or data-frame libraries.

### 1.2 Source code with TPL usage

The benchmark stores the source implementation as the canonical Python reference for this task:

```python
import requests

class FunctionRequestsFetchAverageTemperature:
    BASE_URL = "https://api.fakeweather.dev/v1/temperature"

    def fetch_average_temperature(self, city: str, days: int) -> float:
        params = {"city": city, "days": days}
        resp = requests.get(self.BASE_URL, params=params, timeout=5)
        resp.raise_for_status()

        observations = resp.json()["observations"]
        temps = [float(row["temp_c"]) for row in observations]
        mean_value = sum(temps) / len(temps)
        return round(mean_value, 2)
```

In subsequent stages, this method is treated as the unit of translation. The method body is part of the model input, together with task metadata.

In the released dataset, every task adheres to the canonical naming pattern `function_<library>_<api>.{py,java,cpp}`. Accordingly, this example lives in `function_requests_fetch_average_temperature.py` and defines the matching class `FunctionRequestsFetchAverageTemperature`, with parallel target-language stubs such as `function_requests_fetch_average_temperature.java`.

### 1.3 Library mapping and contract

For each TransLibEval task, the benchmark designer specifies an intended mapping between source-side and target-side libraries. This mapping is used for ground-truth implementations and for human LDA assessment; it is not directly included in the model input.

| Source TPL (Python) | Role                                                        | Target TPL (Java)                                            | Role                                             |
| ------------------- | ----------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| `requests`          | Issue HTTP GET requests, handle errors, parse JSON payloads | `okhttp3.OkHttpClient`, `okhttp3.Request`, `okhttp3.HttpUrl` (HTTP)`org.json.JSONObject`, `org.json.JSONArray` (JSON) | Build and execute requests, parse JSON responses |

On the Python side, the mean and rounding logic rely solely on the standard library (`sum`, `len`, `round`). On the Java side, the expected behavior is reproduced using standard APIs such as `DoubleStream` for aggregation and `BigDecimal` for decimal rounding.

### 1.4 Workflow checklist

For this task, the end-to-end run produces the following classes of artifacts:

| Stage        | Artifact type                                                |
| ------------ | ------------------------------------------------------------ |
| Source prep  | Python source file, TPL declaration, library mapping configuration |
| Translation  | Per-strategy model logs, intermediate IR or retrieval outputs, target code |
| Build & Test | Strategy-specific build logs, JUnit test results for a shared test suite |
| Metrics      | CSR / PR / CA entries recorded per task and per strategy     |
| Human eval   | LDA annotation records and supporting evidence extracted from target code |

------

## 2. Translation Strategies and Intermediate Artifacts

For each of the six strategies, TransLibEval records what information is given to the model, what intermediate artifacts are produced, and where the final Java method is written. The prompts themselves are not reproduced here; instead, we describe the content that conditions the model at each step. Target-side Java code is referenced by filename and structural properties rather than shown in full.

### 2.1 Direct translation (Direct)

In the Direct strategy, the model is conditioned on the Python method and a brief task description. No explicit intermediate representation is requested. The model directly outputs a Java implementation of an instance method `fetchAverageTemperature(String city, int days)` belonging to a `FunctionRequestsFetchAverageTemperature` class.

**Prompt template (per README – Prompts by Strategy).**

```text
System: You are a code translation assistant. Only return the translated code without any additional explanations or text.

User:
Example:Translate the following {from_lang} code to {to_lang}.

Source Code:
{source_example}

Target Code:
{target_example}

Translate the following {from_lang} code to {to_lang}. Only return the translated code without any explanations or additional text.

Source Code:
{input_code}

Target Code:
```

`{source_example}` and `{target_example}` are drawn from the built-in exemplar dictionary, anchoring the model before it sees the true task payload `{input_code}`.



The three IR strategies share a common two-phase template: (1) build an intermediate description that abstracts the Python specifics, persist it under `artifacts/ir_*`, and (2) prompt the model to translate the method again while quoting that IR verbatim. The differences lie in what the IR looks like (reasoning, pseudocode, or prose), but the downstream handling—feeding both the original code and the intermediate file into the generator and saving results under `gen_java/task_0142/ir_*/function_requests_fetch_average_temperature.java`—remains consistent.

### 2.2 IR(CoT): chain-of-thought style IR

IR(CoT) explicitly captures every functional checkpoint before emitting code. The pipeline unfolds as:

1. **Reasoning extraction.** A prompt asks the model to rewrite the Python control flow as numbered natural-language steps. The result is persisted for reproducibility:

```text
artifacts/ir_cot/task_0142/steps.txt
1. Send an HTTP GET request to BASE_URL with query parameters "city" and "days".
2. Apply a timeout of 5 seconds to the HTTP request.
3. If the HTTP status code is not in the 2xx range, raise an error.
4. Parse the JSON response body and extract the "observations" array.
5. For each element in "observations", read the "temp_c" field and cast it to float.
6. Compute the arithmetic mean of all "temp_c" values.
7. Round the mean to two decimal places and return it.
```

2. **IR-conditioned translation.** The translator receives the Python method plus `steps.txt`. Because the IR already commits to using HTTP requests, JSON parsing, averaging, and rounding, the downstream Java code mirrors those operations tightly.

The final Java artifact for this strategy lives under `gen_java/task_0142/ir_cot/function_requests_fetch_average_temperature.java`, accompanied by logs that cite the IR file that guided the generation.

**Prompt template.**

*Stage A (IR extraction)*

```text
System: You are a code analysis assistant that provides structured summaries.

User:
Please read the following source code for the class '{class_name}' and provide a step-by-step chain of thought that describes the logical flow and algorithmic steps.

Focus on the conceptual process rather than language-specific syntax.
Do not quote the exact source code.

Class name: {class_name}. The class name needs to appear.

Here is the code; provide only a step-by-step chain of thought:
{source_code}
```

*Stage B (translation)*

```text
User:
Please generate the {language} code that implements the following functionality:

{chain_of_thought}

Please ensure the code is complete and correctly follows the syntax and conventions for {language}, without including simple usage examples or test code. The code should directly implement the required functionality as described above.
```

### 2.3 IR(pseudocode): pseudocode IR

IR(Pseudocode) follows the same two-phase pattern, except the IR is structured pseudo-code:

```text
artifacts/ir_pseudo/task_0142/pseudocode.txt
function fetch_average_temperature(city, days):
    url = BASE_URL with query parameters "city" and "days"
    response = http_get(url, timeout = 5 seconds)
    if response.status_code is not in [200, 299]:
        raise error
    json = parse_json(response.body)
    temps = [float(obs["temp_c"]) for obs in json["observations"]]
    mean_value = average(temps)
    return round(mean_value, 2)
```

During phase two, the translation model references this pseudo-code line by line and emits Java code that adheres to the same branch/loop layout. The generated method is stored in `gen_java/task_0142/ir_pseudocode/function_requests_fetch_average_temperature.java`, ensuring the pseudo-code file, the raw Python, and the Java output can be inspected together.

**Prompt template.**

*Stage A (IR extraction)*

```text
System: You are a code analysis assistant that provides structured summaries.

User:
Please analyze the following code and generate the corresponding pseudocode. The pseudocode should not reflect any specific language syntax or implementation details, and should focus solely on the core logic and steps of the algorithm. The pseudocode should be structured logically, describing the sequence of operations, decision-making processes, and function calls in a clear and understandable manner.

Write only the pseudocode without any additional explanations or details.

Class name: {class_name}. The class name needs to appear.

Next, I will provide the source code; you must not directly mention the source code in your response:
{source_code}
```

*Stage B (translation)*

```text
User:
Please generate the {language} code that implements the following functionality:

{pseudocode}

Please ensure the code is complete and correctly follows the syntax and conventions for {language}, without including simple usage examples or test code. The code should directly implement the required functionality as described above.
```

### 2.4 IR(summary): functional summary IR

IR(Summary) condenses the behavior into a concise narrative instead of enumerated steps:

```text
artifacts/ir_summary/task_0142/summary.txt
The method contacts a weather API using an HTTP GET request with parameters
city and days. It verifies that the response status indicates success before
parsing the JSON body. It extracts a sequence of Celsius temperatures from
the "observations" array, computes their mean, rounds the result to two
decimal places, and returns the rounded value.
```

The description acts as the IR provided to the translator, supplying enough semantic anchors (HTTP request, JSON parsing, averaging, rounding) without prescribing control structure. The ensuing Java file resides in `gen_java/task_0142/ir_summary/function_requests_fetch_average_temperature.java`.

**Prompt template.**

*Stage A (IR extraction)*

```text
System: You are a code analysis assistant that provides structured summaries.

User:
Please analyze the following code and generate a summary of its functionality. The summary should not focus on specific language syntax, but should explain the key steps, purpose of the code, and overall logic of the program or class in a concise manner.

Class name: {class_name}. The class name should be included in the summary.

Next, I will provide the source code; you must not directly mention the source code in your response:
{source_code}
```

*Stage B (translation)*

```text
User:
Please generate the {language} code that implements the following functionality:

{summary}

Please ensure the code is complete and correctly follows the syntax and conventions for {language}, without including simple usage examples or test code. The code should directly implement the required functionality as described above.
```

### 2.5 RA(method): retrieval-augmented with method-level StackOverflow answers

The RA(Method) pipeline mirrors the procedure described in the paper: rather than retrieving arbitrary code blobs, it gathers StackOverflow answers that are relevant to the full method body. Each task goes through the following steps:

1. **Question synthesis.** A lightweight LLM consumes the complete Python method and produces a single natural-language question that summarizes what the Java translation needs to accomplish. The prompt and response are logged for traceability:

   ```text
   artifacts/retrieval/task_0142/ra_method/query.txt
   '''How can I implement a Java OkHttp client that calls a weather API with
   city/days parameters, parses a JSON observations array, and returns the
   average temperature rounded to two decimals?'''
   ```

2. **StackOverflow retrieval.** The generated question is issued to Google Custom Search (restricted to StackOverflow). The top-ranked question ID is fed into the StackExchange API, and the three highest-voted answers are saved as plain text:

   ```text
   artifacts/retrieval/task_0142/ra_method/answers_question37192562.txt
   OkHttpClient client = new OkHttpClient();
   Request request = new Request.Builder().url(builder.build()).get().build();
   try (Response response = client.newCall(request).execute()) {
       JSONObject root = new JSONObject(response.body().string());
       JSONArray arr = root.getJSONArray("observations");
       double avg = IntStream.range(0, arr.length())
           .mapToDouble(i -> arr.getJSONObject(i).getDouble("temp_c"))
           .average()
           .orElse(Double.NaN);
       return BigDecimal.valueOf(avg).setScale(2, RoundingMode.HALF_UP).doubleValue();
   }
   ```

3. **Answer-conditioned translation.** The translation model receives (a) the original Python method, (b) the retrieved answer text, and (c) strategy metadata. The StackOverflow excerpts act as grounded hints for OkHttp usage, error handling, and rounding semantics. The resulting Java implementation therefore:

- Packages `city` and `days` into a map that drives `HttpUrl.Builder`.
- Uses `OkHttpClient.newCall(...).execute()` plus `org.json` parsing exactly as shown in the answers.
- Aggregates and rounds temperatures following the `BigDecimal` recipe.

The final code is recorded under `gen_java/task_0142/ra_method/function_requests_fetch_average_temperature.java`, together with the query/answer artifacts that explain the retrieval trail.

**Prompt templates.**

```text
Question synthesis — System: You are a helpful assistant for code translation.
Question synthesis — User:
Analyze the following code snippet written in {src}, and generate a single, concise, and well-formed question that summarizes the translation requirements of this code into {tgt}. The question should:
1. Be a simple sentence.
2. Avoid including the original code snippet directly.
3. Clearly describe the key functionality or purpose of the code that needs to be translated.
4. Be enclosed in triple single quotes (''').

Code snippet:
\`\`\`{src}
{code}
\`\`\`

Answer-conditioned translation — System: You are a helpful assistant for code translation.
Answer-conditioned translation — User:
Using the following StackOverflow answers as reference, translate this {src} code into {tgt}:

{answers_concatenated}

{code}

(Fallback when retrieval returns nothing)
User:
Translate the following {src} code into {tgt}:

{code}
```

### 2.6 RA(name): retrieval-augmented with signature-driven name search

RA(Name) follows a two-stage process whose implementation exactly matches the scripts in `code/generate_strategies/RA(name)/`:

1. **Signature extraction.** `signature.py` walks through the source directory (Python/Java/C++ depending on the translation direction) and emits structured metadata per task. For the running example:

   ```text
   signature_out/task_0142.json
   {
       "class_name": "FunctionRequestsFetchAverageTemperature",
       "method": {
           "name": "fetchAverageTemperature",
           "return_type": "double",
           "parameters": [
               {"name": "city", "type": "String"},
               {"name": "days", "type": "int"}
           ],
           "throws": ["IOException"]
       }
   }
   ```

2. **Name-only StackOverflow search.** `Search.py` (spelled `Serch.py` in the C++ folder) iterates over the extracted signatures, issues queries of the form `"<target language> <method name>"`, and stores the resulting StackOverflow question IDs and top answers inside `function_stackoverflow_answers/<target>_function_results/*.json`:

   ```text
   function_stackoverflow_answers/java_function_results/task_0142_results.json
   [
       {
           "function": "fetchAverageTemperature",
           "status": "success",
           "question": {
               "question_id": "37192562",
               "title": "Java OkHttp GET request returning JSON array"
           },
           "answers": [
               "OkHttpClient client = new OkHttpClient.Builder()....",
               "If you need rounding, wrap the average in BigDecimal..."
           ]
       }
   ]
   ```

3. **Signature-aware prompting.** Each provider script combines the signature JSON, the retrieved answers (or the original source file if no answers exist), and a target-language-specific instruction template. Because the retrieval step only depends on method/class names, it can latch onto idiomatic StackOverflow examples even when the source implementation is terse.

The generated Java file in this strategy again appears under `gen_java/task_0142/ra_name/function_requests_fetch_average_temperature.java`, but every prediction is now traceable to the `signature_out/` and `function_stackoverflow_answers/` artifacts created beforehand.

**Prompt template.**

```text
System: You are a world-class code translation assistant.

User:
You are a world-class expert in code generation with deep mastery of translating algorithmic {from_lang} class methods into {target} implementations.

Below are the precise function signature details and either community-sourced reference implementations or the original {from_lang} code as fallback. Your task is to generate clean, idiomatic, and fully functional {target} code that exactly matches the behavior.

=== Function Signature & Metadata ===
{sig_json}

=== Reference Implementation ===
{ref_impl}

Produce only the final {target} code. Do not include any explanations, comments, or extra text.

Begin {target} code now:
```

### 3. Build and Test Suites

### 3.1 Build and execution command

For each strategy, TransLibEval injects the generated `function_requests_fetch_average_temperature.java` into a Maven module and runs a shared test suite. The build command used in this example run is:

```bash
export TARGET_LANG=java
mvn -pl function_requests_fetch_average_temperature -Dtest=FunctionRequestsFetchAverageTemperatureTest test
```

A typical build log for a successful compilation and test execution contains entries of the following form:

```text
[INFO] --- maven-compiler-plugin:3.11.0:compile ---
[INFO] Compiling 1 source file to target/classes
[INFO] --- maven-surefire-plugin:3.2.5:test ---
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

Separate logs are stored per strategy, for example:

- `logs/task_0142/direct/compile.log` and `logs/task_0142/direct/test.log`
- `logs/task_0142/ir_cot/compile.log` and `logs/task_0142/ir_cot/test.log`, and so on.

### 3.2 Test suite design

The test suite for this task consists of five JUnit test cases, each corresponding to a behavioral category that is shared across tasks in the benchmark. The tests exercise nominal, boundary, error, and robustness conditions.

| Test case ID          | Input characteristics                      | Bucket category     | Expected outcome                                 |
| --------------------- | ------------------------------------------ | ------------------- | ------------------------------------------------ |
| `test_nominal_city`   | Valid city name, `days = 5`                | Nominal semantics   | Correct mean is returned                         |
| `test_edge_zero_day`  | `days = 0`                                 | Boundary adherence  | Defined behavior on empty window (e.g., `NaN`)   |
| `test_missing_field`  | One observation missing the `temp_c` field | Exception semantics | Appropriate exception                            |
| `test_type_violation` | `city = None` (or analogous invalid input) | Type conformance    | Error or exception                               |
| `test_large_window`   | `days = 30`                                | Resource resilience | Completes within time and returns a valid result |

For each strategy, the test runner records the number of tests executed, the number passed, and the status of individual test cases in a JSON log.

------

## 4. Automatic Metrics (CSR, PR, CA)

TransLibEval computes three automatic metrics per task and per strategy:

- Compilation Success Rate (CSR): for a single task in one run, CSR is 1 if compilation succeeds and 0 otherwise.
- Pass Rate (PR): the fraction of test cases that pass, i.e., `tests_passed / tests_total`.
- Computational Accuracy (CA): 1 if all test cases pass (i.e., PR = 1.0), and 0 if at least one test fails.

For this task and example run, the metrics are logged as:

| Strategy       | CSR  | PR   | CA   |
| -------------- | ---- | ---- | ---- |
| Direct         | 1    | 0.8  | 0    |
| IR(CoT)        | 1    | 1.0  | 1    |
| IR(Pseudocode) | 1    | 1.0  | 1    |
| IR(Summary)    | 1    | 0.8  | 0    |
| RA(Method)     | 1    | 1.0  | 1    |
| RA(Name)       | 1    | 1.0  | 1    |

These values are derived directly from the build and test logs. For example, for the Direct strategy, the Java code compiles (`CSR = 1`), but fails one boundary-related test case (`PR = 4/5 = 0.8`, `CA = 0`), whereas the IR(CoT) and RA-based strategies pass all five tests.

------

## 5. Human Evaluation: Library Dependency Awareness (LDA)

### 5.1 Evaluation procedure

Beyond automatic metrics, TransLibEval includes a human evaluation phase that focuses on library dependency awareness. For each `(task, strategy)` pair, annotators inspect the generated Java implementation (and any helper classes it invokes) and verify whether the intended target-side TPL responsibilities are actually realized.

The inspection proceeds as follows. Annotators first consult the library mapping for the task to identify which target-side libraries should be responsible for HTTP communication, JSON parsing, and any other TPL-related functionality. They then open the generated `function_requests_fetch_average_temperature.java` (and referenced helper classes, such as `WeatherGateway` or `RoundingUtils`) and locate the relevant constructor calls, method invocations, and imports. Finally, they assign a binary label `LDA = 1` if the necessary TPLs are correctly employed for their intended roles, or `LDA = 0` if the implementation either omits these libraries or misuses them in a way that breaks the logical mapping.

### 5.2 Example inspection record

For `task_0142` and strategy IR(CoT), the annotator’s evidence record has the following structure:

| Checkpoint               | Evidence snippet (file and line)                             | Conclusion |
| ------------------------ | ------------------------------------------------------------ | ---------- |
| HTTP client              | `private final OkHttpClient httpClient = new OkHttpClient.Builder().callTimeout(5, TimeUnit.SECONDS).build();` | Satisfied  |
| Request construction     | Usage of `HttpUrl.parse(BASE_URL).newBuilder().addQueryParameter("city", city)...` in `fetchAverageTemperature` | Satisfied  |
| JSON parsing             | `JSONObject root = new JSONObject(response.body().string());` followed by `root.getJSONArray("observations")` | Satisfied  |
| Aggregation and rounding | Aggregation via streams and rounding via `BigDecimal.setScale(2, RoundingMode.HALF_UP)` | Satisfied  |

The corresponding LDA entry is:

```text
annotations/lda/task_0142_ir_cot.txt
strategy: ir_cot
uses_okhttp: yes
uses_org_json: yes
numeric_behavior_matches: yes
lda: 1
```

Analogous records are stored for other strategies. In this example run, IR(CoT), IR(Pseudocode), IR(Summary), RA(Method), and RA(Name) all achieve `LDA = 1`, as they either use `OkHttp` and `org.json` directly or rely on helper abstractions built on them. The Direct strategy compiles and passes most tests but is labeled with `LDA = 0` because it implements HTTP behavior using low-level JDK networking rather than the mapped TPL family.
