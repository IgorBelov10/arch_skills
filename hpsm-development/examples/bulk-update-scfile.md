# Пример: массовое обновление записей через SCFile

**Задача:** пройтись по всем записям `device`, найденным по произвольному запросу, и обновить поле времени.

```javascript
/**
 * @param {string} queryString   - строка запроса SM (синтаксис как в doSelect)
 * @param {string} timeFieldName - имя поля для записи текущего времени
 * @returns {object} - { total, updated, failed, errors }
 */
function bulkUpdateDeviceSystemTime(queryString, timeFieldName) {
    var stats = { total: 0, updated: 0, failed: 0, errors: [] };

    if (!queryString || !timeFieldName) {
        stats.errors.push("queryString and timeFieldName are required");
        return stats;
    }

    var deviceFile = new SCFile("device");
    var rc = deviceFile.doSelect(queryString);

    if (rc != RC_SUCCESS) {
        print("WARN: bulkUpdateDeviceSystemTime: No records found or query failed. RC=" + rc + ", query=" + queryString);
        return stats;
    }

    var now = new Date(); // см. references/js-api.md — проверить формат для конкретного поля

    while (rc == RC_SUCCESS) {
        stats.total++;
        try {
            deviceFile.setFields(timeFieldName, now);
            var updateRc = deviceFile.doUpdate();

            if (updateRc == RC_SUCCESS) {
                stats.updated++;
            } else {
                stats.failed++;
                stats.errors.push("Update failed for record #" + stats.total +
                    ", RC=" + updateRc + ", messages=" + deviceFile.getMessages());
            }
        } catch (e) {
            stats.failed++;
            stats.errors.push("Exception on record #" + stats.total + ": " + e.toString());
        }
        rc = deviceFile.getNext();
    }

    print("INFO: bulkUpdateDeviceSystemTime: Total=" + stats.total + ", Updated=" + stats.updated + ", Failed=" + stats.failed);

    return stats;
}
```

**Разбор паттерна для аналогичных задач (массовые операции по любому объекту):**
1. Параметризовать запрос и целевое поле — не хардкодить.
2. Всегда собирать статистику (`total/updated/failed`) — фоновые массовые операции без отчёта потом невозможно диагностировать.
3. Обрабатывать ошибку на уровне отдельной записи (try/catch внутри цикла), чтобы одна проблемная запись не обрывала всю пачку.
4. Явно проверять RC после `doUpdate()`/`doInsert()` — не полагаться только на try/catch (см. `references/rad-language.md`).
5. Логировать итог одним сообщением в конце, а не по каждой записи (иначе лог захламляется на больших объёмах).
6. При больших объёмах (десятки тысяч записей) — обсуждать с пользователем пакетную обработку/лимит за один проход, а не один гигантский цикл.
