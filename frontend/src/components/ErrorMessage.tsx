export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="py-20 text-center">
      <p className="text-sm text-red-600">{message}</p>
    </div>
  )
}
