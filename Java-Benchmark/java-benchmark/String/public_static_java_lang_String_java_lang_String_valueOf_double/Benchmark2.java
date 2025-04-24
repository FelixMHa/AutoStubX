

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("8.3637196978335334E18") && output_2.equals("9.572928649148481E81")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

