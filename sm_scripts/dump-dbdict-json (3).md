# Дамп dbdict в JSON — ScriptLibrary

## Что подтверждено, а что нет

**Подтверждено официальной документацией Micro Focus (не выдумано):**
- `dbdict` — обычная таблица SM, читается через `new SCFile("dbdict")` и `doSelect()`, как любая другая (см. `js-api.md`).
- `SCFile.getXML()` — документированный метод, возвращающий запись в XML (имена полей + значения, включая массивы/структуры).
- SM использует Rhino как JS-движок, а в официальном JS reference guide отдельно документирован объект `XML` — это указывает на поддержку **E4X** (ECMAScript for XML, стандартное для Rhino расширение JS, НЕ проприетарная вещь SM). Ниже используется стандартный E4X-объект (`.children()`, `.name()`, `.length()`) с обычным индексным циклом — **не** конструкция `for each`, которая на вашей версии не работает (см. правку ниже).

**НЕ подтверждено (и в этом коде сознательно нет):**
- Прямая запись в файл на диске сервера из ScriptLibrary JS — я не нашёл документированного API для этого.
- Точная семантика кнопки **"Выполнить"** в толстом клиенте (запускает ли она весь файл целиком сверху вниз, или требует выбора конкретной функции/выделения кода) — код ниже написан так, чтобы работать в обоих правдоподобных случаях: в конце файла есть однострочный вызов с явно заданной таблицей, так что "выполнить весь файл" должно сработать; если у вас другая механика — потребуется адаптация точки входа.
- **Имя таблицы ScriptLibrary в вызове `new SCFile(...)` ниже — `"ScriptLibrary"` (с заглавных букв).** Это взято дословно из вашего же реального `.unl`-примера (там оно встречалось именно в таком регистре как значение `Filename` в запросе). Не факт, что для `doInsert()`/`doSelect()` регистр обязателен именно такой — если вставка не найдёт таблицу, попробуйте `"scriptlibrary"` в нижнем регистре.
- **Имя поля `script`** — беру как есть, вы сами его назвали.

## Код

```javascript
/**
 * ScriptLibrary: DumpDbdictJson
 *
 * Дампит структуру dbdict указанной таблицы в JSON и сохраняет результат
 * в НОВУЮ запись ScriptLibrary (имя которой включает дату/время запуска),
 * записывая JSON в поле `script`. Так результат остаётся внутри самого SM
 * и виден в Tailoring, без необходимости в файловом I/O с диска сервера.
 */

// === Перед запуском укажите нужную таблицу ===
var TARGET_TABLE = "device";

/**
 * Получить dbdict-запись таблицы и вернуть её как JSON-строку.
 * @param {string} tableName - имя таблицы (например "device", "schedule")
 * @returns {string|null} JSON-строка либо null, если запись не найдена
 */
function getDbdictAsJson(tableName) {
    var dbdictFile = new SCFile("dbdict");
    var rc = dbdictFile.doSelect('name="' + tableName + '"');

    if (rc != RC_SUCCESS) {
        print("ERROR: dbdict record not found for table '" + tableName + "', RC=" + rc);
        return null;
    }

    var xmlText = dbdictFile.getXML(); // подтверждённый метод SCFile
    var xmlObj = parseXmlSafely(xmlText);

    if (xmlObj == null) {
        print("ERROR: не удалось распарсить XML для таблицы '" + tableName + "' (см. parseXmlSafely)");
        return null;
    }

    var jsonObj = xmlToJson(xmlObj);
    return JSON.stringify(jsonObj, null, 2);
}

/**
 * Безопасно оборачивает getXML()-текст в валидный для E4X документ.
 *
 * Две известные причины, по которым "new XML(text)" может отказаться
 * парсить текст от getXML():
 *  1. XML-декларация в начале (`<?xml version="1.0"?>`) - спецификация E4X
 *     прямо запрещает её внутри XML()-конструктора.
 *  2. Несколько элементов верхнего уровня без общего корня (getXML() может
 *     вернуть просто список полей записи, без единого корневого тега) -
 *     E4X ожидает ровно один корневой узел.
 *
 * Функция убирает XML-декларацию (если есть) и всегда оборачивает
 * содержимое в искусственный <root>...</root> - это не меняет результат
 * xmlToJson(), так как та смотрит на ДЕТЕЙ переданного узла, а не на его
 * собственное имя, и работает одинаково что с "родным" корнем, что с
 * искусственной обёрткой.
 */
function parseXmlSafely(xmlText) {
    var cleaned = xmlText.replace(/^\s*<\?xml[^>]*\?>\s*/i, "");
    try {
        return new XML("<root>" + cleaned + "</root>");
    } catch (e) {
        lib.logmessage("ERROR", "parseXmlSafely", "XML parse failed: " + e.toString());
        return null;
    }
}

/**
 * Общий рекурсивный конвертер E4X XML -> обычный JS-объект.
 * - элемент без дочерних элементов -> строка (текстовое содержимое)
 * - элемент с несколькими одноимёнными детьми -> массив
 * - элемент с разными по имени детьми -> объект
 *
 * Generic алгоритм, не завязан на конкретные имена тегов dbdict.
 */
function xmlToJson(xmlNode) {
    var children = xmlNode.children();
    var count = children.length();

    if (count === 0) {
        return xmlNode.toString();
    }

    var result = {};
    for (var i = 0; i < count; i++) {
        var child = children[i];       // индексный доступ к XMLList, вместо "for each"
        var name = child.name().toString();
        var value = xmlToJson(child);

        if (result.hasOwnProperty(name)) {
            if (!(result[name] instanceof Array)) {
                result[name] = [result[name]];
            }
            result[name].push(value);
        } else {
            result[name] = value;
        }
    }
    return result;
}

/**
 * Строит уникальное имя новой ScriptLibrary-записи с датой/временем запуска.
 * Использует обычный JS Date (не запись в дата-поле SM, а просто строка
 * в имени) - это безопасно, формат даты для полей типа date/time тут
 * не при чём.
 */
function buildDumpScriptLibraryName(tableName) {
    var now = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    var stamp = now.getFullYear() +
        pad(now.getMonth() + 1) +
        pad(now.getDate()) + "_" +
        pad(now.getHours()) +
        pad(now.getMinutes()) +
        pad(now.getSeconds());
    return "DbdictDump_" + tableName + "_" + stamp;
}

/**
 * Главная функция: дампит dbdict таблицы в JSON и сохраняет результат
 * в новую запись ScriptLibrary (поле name = сгенерированное уникальное имя,
 * поле script = сам JSON).
 */
function dumpDbdictToScriptLibrary(tableName) {
    var json = getDbdictAsJson(tableName);
    if (json == null) {
        return; // сообщение об ошибке уже напечатано в getDbdictAsJson
    }

    var slName = buildDumpScriptLibraryName(tableName);

    var slFile = new SCFile("ScriptLibrary"); // см. предупреждение про регистр выше
    slFile.name = slName;
    slFile.script = json;

    var rc = slFile.doInsert();

    if (rc == RC_SUCCESS) {
        print("OK: dbdict для '" + tableName + "' сохранён в ScriptLibrary '" + slName + "'");
    } else {
        print("ERROR: не удалось создать ScriptLibrary '" + slName +
            "', RC=" + rc + ", messages=" + slFile.getMessages());
    }
}

// === Точка входа для кнопки "Выполнить" ===
dumpDbdictToScriptLibrary(TARGET_TABLE);
```

## Что обязательно проверить при первом прогоне

1. **Работает ли теперь парсинг.** Оборачивание в `<root>...</root>` и обрезка XML-декларации закрывают две известные причины отказа `new XML(...)`. Если и это не помогло — пришлите (можно частично) реальный текст, который возвращает `getXML()` для одной записи, и я перепишу конвертер без E4X вообще, на regex-парсере под конкретный формат.
2. **Найдёт ли `new SCFile("ScriptLibrary")` реальную таблицу** — если `doInsert()` вернёт ошибку "таблица не найдена" или похожую, попробуйте `"scriptlibrary"` в нижнем регистре.
3. **Реальная форма XML от `getXML()` для dbdict** — посмотрите глазами на первый результат в поле `script` новой записи, прежде чем полагаться на структуру.
4. **Права оператора** — создание новой записи ScriptLibrary через `doInsert()` требует соответствующих прав у оператора, из-под которого выполняется скрипт (см. `errors.md`, категория "права доступа") — если вставка тихо не проходит, это вероятная причина.

## Дальнейший шаг: перенос в иерархию skill'а

Результат остаётся внутри SM (новая запись ScriptLibrary `DbdictDump_<таблица>_<дата>`). Дальше — вручную: открыть эту запись, скопировать содержимое поля `script` (это готовый JSON) и сохранить как `references/schemas/<таблица>.json` в этом skill (см. `references/schemas/README.md`). Сами записи `DbdictDump_*` можно потом удалить из SM или оставить как историю — это уже не часть работы skill'а.

