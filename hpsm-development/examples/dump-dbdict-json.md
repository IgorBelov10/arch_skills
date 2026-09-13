# Дамп dbdict — ScriptLibrary (XML, без конвертации в JSON)

## Почему XML, а не JSON

Изначальная идея была сконвертировать `getXML()` в JSON через E4X. На практике на этом инстансе движок оказался слишком урезан для этого (не работали `for each`, регулярки-литералы, и в итоге сам `new XML(...)` не смог распарсить то, что возвращает `getXML()` — причина не выяснена до конца, тратить время на дальнейшее выяснение не стали). Решение: **не конвертировать вообще, сохранять сырой XML как есть.** Он всё равно человеко- и машиночитаемый (имена полей и значения видны прямо в тексте) — просто не JSON.

## Что подтверждено

- `dbdict` — обычная таблица SM, читается через `new SCFile("dbdict")` и `doSelect()` (см. `js-api.md`).
- `SCFile.getXML()` — документированный метод, возвращающий запись в XML.
- Остальное (E4X, `for each`, regex-литералы) — на вашем инстансе не сработало, поэтому в коде ниже сознательно не используется.

## Не подтверждено

- Прямая запись в файл на диске сервера из ScriptLibrary JS — не нашёл документированного API, поэтому результат сохраняется в новую запись `ScriptLibrary` (поле `script`), а не на диск.
- Точная семантика кнопки "Выполнить" в толстом клиенте — код написан так, чтобы работать, если она просто прогоняет весь файл сверху вниз.
- Регистр имени таблицы `"ScriptLibrary"` — взят из вашего `.unl`-примера; если `doInsert()` не найдёт таблицу, попробуйте `"scriptlibrary"`.

## Код

```javascript
/**
 * ScriptLibrary: DumpDbdictJson
 *
 * Дампит dbdict указанной таблицы как XML (без конвертации в JSON — см.
 * пояснение выше) и сохраняет результат в НОВУЮ запись ScriptLibrary
 * (имя включает дату/время запуска), в поле `script`.
 */

// === Перед запуском укажите нужную таблицу ===
var TARGET_TABLE = "device";

/**
 * Получить dbdict-запись таблицы как XML-текст.
 * @param {string} tableName
 * @returns {string|null}
 */
function getDbdictAsXml(tableName) {
    var dbdictFile = new SCFile("dbdict");
    var rc = dbdictFile.doSelect('name="' + tableName + '"');

    if (rc != RC_SUCCESS) {
        print("ERROR: dbdict record not found for table '" + tableName + "', RC=" + rc);
        return null;
    }

    return dbdictFile.getXML(); // подтверждённый метод SCFile, сырой XML как есть
}

/**
 * Строит уникальное имя новой ScriptLibrary-записи с датой/временем запуска.
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
 * Главная функция: дампит dbdict таблицы и сохраняет XML в новую запись
 * ScriptLibrary (поле name = сгенерированное уникальное имя, поле script = XML).
 */
function dumpDbdictToScriptLibrary(tableName) {
    var xml = getDbdictAsXml(tableName);
    if (xml == null) {
        return; // сообщение об ошибке уже напечатано в getDbdictAsXml
    }

    var slName = buildDumpScriptLibraryName(tableName);

    var slFile = new SCFile("ScriptLibrary"); // см. предупреждение про регистр выше
    slFile.name = slName;
    slFile.script = xml;

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

1. **Найдёт ли `new SCFile("ScriptLibrary")` реальную таблицу** — если `doInsert()` вернёт ошибку "таблица не найдена", попробуйте `"scriptlibrary"` в нижнем регистре.
2. **Права оператора** — создание записи через `doInsert()` требует прав у оператора, из-под которого выполняется скрипт (см. `errors.md`, категория "права доступа").
3. **Размер XML для больших таблиц** — если dbdict большой таблицы (много полей) даёт очень длинный XML, стоит проверить, нет ли у поля `script` практического ограничения по длине на этом инстансе.

## Дальнейший шаг: перенос в иерархию skill'а

Результат остаётся внутри SM (новая запись ScriptLibrary `DbdictDump_<таблица>_<дата>`, поле `script` содержит XML). Дальше — вручную: открыть эту запись, скопировать содержимое поля `script` и сохранить как `references/schemas/<таблица>.xml` в этом skill (см. `references/schemas/README.md` — формат там теперь XML, не JSON). Сами записи `DbdictDump_*` можно потом удалить из SM или оставить как историю.
