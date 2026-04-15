function generateAdminReport(PDO $pdo, array $post): array
{
    [$sql, $params] = buildReportQuery($post);