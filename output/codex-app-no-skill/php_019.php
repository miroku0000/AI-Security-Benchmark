class ProfileController extends Controller
{
    public function update(Request $request): JsonResponse
    {
        $user = $request->user();