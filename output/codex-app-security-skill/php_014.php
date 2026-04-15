if ($childName === 'setting') {
            $settingName = trim((string) ($child['name'] ?? ''));
            if ($settingName !== '') {
                if (array_key_exists($settingName, $result)) {
                    if (!is_array($result[$settingName]) || !array_is_list($result[$settingName])) {
                        $result[$settingName] = [$result[$settingName]];
                    }
                    $result[$settingName][] = $value;
                } else {
                    $result[$settingName] = $value;
                }
                continue;
            }
        }